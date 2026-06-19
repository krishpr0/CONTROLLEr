/*
 * timer.h - Timer and System Event Driver
 *
 * Hardware timer and periodic interrupt handling for the ASM2464PD
 * USB4/Thunderbolt to NVMe bridge. Provides millisecond-resolution delays
 * and periodic polling for system events.
 *
 * ===========================================================================
 * HARDWARE ARCHITECTURE
 * ===========================================================================
 * The ASM2464PD has 4 independent hardware timers:
 *
 *   Timer0 (0xCC10-0xCC13): Main system tick timer, drives periodic ISR
 *   Timer1 (0xCC16-0xCC19): Protocol timeouts
 *   Timer2 (0xCC1C-0xCC1F): USB timing
 *   Timer3 (0xCC22-0xCC25): Idle timeout management
 *
 * Clock source: 114MHz system clock
 *
 * ===========================================================================
 * TIMER CSR REGISTER BITS
 * ===========================================================================
 * Each timer has a CSR (Control/Status Register) with these bits:
 *
 *   Bit 0: Enable - Start/stop timer counting
 *   Bit 1: Done/Complete - Timer reached threshold
 *          - SET by hardware when timer expires
 *          - Firmware polls this bit waiting for completion
 *          - Emulator auto-sets after 2+ reads to prevent infinite loops
 *   Bit 2: Clear - Write 1 to clear Done bit and reset timer
 *          - Resets poll count in emulator
 *   Bits 3-7: Reserved
 *
 * ===========================================================================
 * POLLING PATTERN
 * ===========================================================================
 * Firmware uses this polling pattern for timer/DMA operations:
 *
 *   1. Configure timer (write DIV, threshold, enable)
 *   2. Poll timer CSR waiting for Done bit (bit 1) to be SET
 *   3. When Done bit is SET, operation is complete
 *   4. Write timer CSR with Clear bit (bit 2) to reset for next use
 *
 * Emulator behavior (prevents infinite loops):
 *   - First 1-2 reads: Return current value (bit 1 CLEAR)
 *   - After 2+ reads: Auto-set bit 1 (Done/Complete)
 *   - Write with bit 2 SET: Clears bit 1, resets poll count
 *
 * ===========================================================================
 * REGISTER MAP (0xCC10-0xCC8F)
 * ===========================================================================
 *
 * Timer 0 (System tick):
 *   0xCC10  Timer0 DIV       Clock divider (bits 0-2: prescaler)
 *   0xCC11  Timer0 CSR       Control/Status (see CSR bits above)
 *   0xCC12-13 Timer0 Threshold (16-bit count value, little-endian)
 *
 * Timer 1 (Protocol timeout):
 *   0xCC16  Timer1 DIV       Clock divider
 *   0xCC17  Timer1 CSR       Control/Status
 *   0xCC18-19 Timer1 Threshold (16-bit)
 *
 * Timer 2 (USB timing):
 *   0xCC1C  Timer2 DIV       Clock divider
 *   0xCC1D  Timer2 CSR       Control/Status
 *   0xCC1E-1F Timer2 Threshold (16-bit)
 *
 * Timer 3 (Idle timeout):
 *   0xCC22  Timer3 DIV       Clock divider
 *   0xCC23  Timer3 CSR       Control/Status
 *   0xCC24  Timer3 Idle Timeout
 *
 * CPU/System Control:
 *   0xCC32  CPU_SYS_STATE    System state (bit 0 checked during init)
 *   0xCC33  CPU_EXEC_STAT    CPU execution status (default 0x04)
 *                            Bit 2: Event flag (checked in ISR)
 *   0xCC37  CPU_CTRL         CPU control register
 *   0xCC3B-3F CPU control registers 2-5
 *
 * Timer/DMA Combined:
 *   0xCC81  TIMER_DMA_CTRL   Timer/DMA control
 *   0xCC82  TIMER_DMA_ADDR_LO Address low byte
 *   0xCC83  TIMER_DMA_ADDR_HI Address high byte
 *   0xCC89  TIMER_DMA_STATUS Timer/DMA status
 *                            Bit 1: Complete (auto-sets after 2+ reads)
 *
 * ===========================================================================
 * TIMER DIV REGISTER BITS
 * ===========================================================================
 *   Bits 0-2: Prescaler select (divides clock by 2^N)
 *             0 = divide by 1, 1 = divide by 2, 2 = divide by 4, etc.
 *   Bit 3: Timer enable/disable bit
 *   Bits 4-7: Reserved
 *
 * ===========================================================================
 * TYPICAL TIMER0 CONFIGURATION (from 0xAD72)
 * ===========================================================================
 *   - Prescaler: 3 (divide by 8)
 *   - Threshold: 0x0028 (40 counts)
 *   - Results in ~1ms tick at 114MHz / 8 / 40 ≈ 356kHz → ~2.8us per tick
 *
 * ===========================================================================
 * TIMER0 ISR FLOW (0x44D7-0x4582)
 * ===========================================================================
 * The Timer0 ISR handles various system events:
 *
 *   1. Save context (ACC, B, DPTR, PSW, R0-R7) - 0x44D7-0x44F2
 *   2. Check 0xC806 bit 0 → call 0x0507 → 0xA79C (idle timeout) - 0x44F4
 *   3. Check 0xCC33 bit 2 → write 0x04, call 0x038B - 0x44FE
 *   4. Check 0xC80A bit 6 → call 0x0516 → 0xAE89 (UART debug) - 0x450B
 *   5. If 0x09F9 & 0x83 != 0: - 0x4515
 *      - Check 0xC80A bit 5 → call 0x05F2 → Bank1 0xA08B (async event)
 *      - Check 0xC80A bit 4 → call 0x0570 → 0xBF1C (link event)
 *      - Check 0xEC06 bit 0 → write 0x01 to 0xEC04, check 0x0AF0 bit 5
 *        - If bit 5 set: clear bits 6,7 of 0xE7E3
 *        - Call NVMe completion handler
 *   6. Check 0xC80A & 0x0F → call error handler
 *   7. Check 0xC806 bit 4 → call system event stub
 *   8. Restore context and RETI - 0x455E-0x4582
 *
 * ===========================================================================
 * INTERRUPT STATUS REGISTERS
 * ===========================================================================
 *   0xC806  INT_SYSTEM     System interrupt status
 *                          Bit 0: Idle timeout pending
 *                          Bit 4: System event pending
 *   0xC80A  INT_PCIE_NVME  PCIe/NVMe interrupt status
 *                          Bit 4: PCIe link event
 *                          Bit 5: PCIe async event
 *                          Bit 6: UART debug pending
 *                          Bits 0-3: PCIe error flags
 *   0xCC33  CPU_EXEC_STAT  CPU execution status
 *                          Bit 2: Timer event flag
 *   0xEC06  NVME_EVENT_ST  NVMe event status (bit 0)
 *   0xEC04  NVME_EVENT_ACK NVMe event acknowledge
 *
 * ===========================================================================
 * EMULATOR BEHAVIOR
 * ===========================================================================
 * The emulator implements timer behavior to prevent infinite polling loops:
 *
 *   Timer CSR (0xCC11/17/1D/23):
 *     - Tracks poll count per address
 *     - After 2+ reads, auto-sets bit 1 (Done/Complete)
 *     - Write with bit 2 (Clear) resets poll count and clears bit 1
 *
 *   Timer DMA Status (0xCC89):
 *     - Same polling behavior as timer CSR
 *     - Auto-sets bit 1 after 2+ reads
 *
 * ===========================================================================
 * EVENT HANDLERS
 * ===========================================================================
 *   - timer_idle_timeout_handler(): Detect host inactivity
 *   - timer_pcie_link_event(): PCIe link state changes
 *   - timer_nvme_completion(): Poll NVMe completion queues
 *   - timer_uart_debug_output(): Periodic debug messages
 */
#ifndef _TIMER_H_
#define _TIMER_H_

#include "../types.h"

/* Timer ISR and control */
void timer0_isr(void) __interrupt(1) __using(0);                /* 0x44D7-0x4582 (ISR body) */
void timer0_csr_ack(void);                      /* writes 0x04 then 0x02 to timer CSR */
void timer0_wait_done(void);                    /* poll timer CSR bit 1, then ack */
void timer1_check_and_ack(void);                /* 0x20be-0x2111 */

/* Timer event handlers - dispatch stubs that jump to actual handlers */
void timer_idle_timeout_handler(void);          /* 0x0507 -> 0xA79C (idle timeout) */
void timer_uart_debug_output(void);             /* 0x0516 -> 0xAE89 (UART debug) */
void timer_pcie_link_event(void);               /* 0x0570 -> 0xBF1C (PCIe link) */
void timer_pcie_async_event(void);              /* 0x05F2 -> Bank1 0xA08B (async) */
void timer_system_event_stub(void);             /* 0x061a -> Bank1 0xEEDD (system event) */
void timer_pcie_error_handler(void);            /* 0x054d -> Bank1 0xE924 (error) */
void timer_nvme_completion(void);               /* 0x048f -> Bank1 0xC0E5 (NVMe) */
void timer_link_status_handler(void);           /* 0x04d0 -> 0xE0B4 (link status) */

/* System handlers */
void system_interrupt_handler(void);            /* 0x0520 -> 0x8A81 (state init) */
void system_timer_handler(void);                /* 0x061a -> Bank1 0xEEDD */

/* Timer configuration */
void timer_wait(uint8_t timeout_lo, uint8_t timeout_hi, uint8_t mode);  /* 0xe726-0xe72f (Bank 1) */
void timer_config_trampoline(uint8_t p1, uint8_t p2, uint8_t p3);       /* 0x0511-0x0514 */
void timer_event_init(void);                    /* 0x4532-0x45ff */
void timer_trigger_e726(void);                  /* 0xe726-0xe72f (Bank 1) */
void timer_phy_config_e57d(uint8_t param);      /* 0xe57d-0xe5fd (Bank 1) */

/* Delay functions */
void delay_loop_adb0(void);                     /* 0xadb0-0xade5 */
void delay_short_e89d(void);                    /* 0xe89d-0xe8a8 */
void delay_wait_e80a(uint16_t delay, uint8_t flag);  /* 0xe80a-0xe81x */

/* Timer enable/disable */
void reg_timer_setup_and_set_bits(void);        /* 0xbcf2-0xbd04 */
void reg_timer_init_and_start(void);            /* 0xbd05-0xbd13 */
void reg_timer_clear_bits(void);                /* 0xbd14-0xbd22 */
void timer_clear_ctrl_bit1(void);               /* 0xbd41-0xbd48 */
void timer0_configure(uint8_t div_bits, uint8_t threshold_hi, uint8_t threshold_lo);  /* 0xad72-0xad85 */
void timer0_reset(void);                        /* 0xad86-0xad94 */

#endif /* _TIMER_H_ */
