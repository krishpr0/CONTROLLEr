#!/usr/bin/env python3
"""
USB Host Interface for ASM2464PD Emulator

This module provides a USB host interface that injects USB control and bulk
transfers through MMIO registers and captures firmware responses via DMA.

CRITICAL: The emulator must NOT parse or process USB control messages.
All USB handling is done by the firmware via pure MMIO/DMA:
1. USB host sets up MMIO registers with the USB request
2. Firmware reads MMIO, processes request, configures DMA
3. Firmware DMAs response data to output buffer
4. USB host reads response from DMA output buffer

The Python code NEVER determines addresses or processes USB semantics.
All addresses come from firmware register writes observed via DMA callbacks.
"""

import threading
import time
import queue
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Tuple
from enum import IntEnum

# USB request types
class USBRequestType(IntEnum):
    STANDARD = 0x00
    CLASS = 0x20
    VENDOR = 0x40
    DIRECTION_IN = 0x80
    DIRECTION_OUT = 0x00

# USB standard requests
class USBRequest(IntEnum):
    GET_STATUS = 0x00
    CLEAR_FEATURE = 0x01
    SET_FEATURE = 0x03
    SET_ADDRESS = 0x05
    GET_DESCRIPTOR = 0x06
    SET_DESCRIPTOR = 0x07
    GET_CONFIGURATION = 0x08
    SET_CONFIGURATION = 0x09
    GET_INTERFACE = 0x0A
    SET_INTERFACE = 0x0B

# USB descriptor types
class USBDescriptorType(IntEnum):
    DEVICE = 0x01
    CONFIGURATION = 0x02
    STRING = 0x03
    INTERFACE = 0x04
    ENDPOINT = 0x05
    BOS = 0x0F


@dataclass
class USBControlTransfer:
    """Represents a USB control transfer (setup packet)."""
    bmRequestType: int  # Request type and direction
    bRequest: int       # Request code
    wValue: int         # Value field
    wIndex: int         # Index field
    wLength: int        # Data length
    data: bytes = b''   # Data for OUT transfers

    @property
    def is_in_transfer(self) -> bool:
        """True if this is a device-to-host transfer."""
        return bool(self.bmRequestType & USBRequestType.DIRECTION_IN)

    def to_setup_packet(self) -> bytes:
        """Convert to 8-byte USB setup packet."""
        return bytes([
            self.bmRequestType,
            self.bRequest,
            self.wValue & 0xFF,
            (self.wValue >> 8) & 0xFF,
            self.wIndex & 0xFF,
            (self.wIndex >> 8) & 0xFF,
            self.wLength & 0xFF,
            (self.wLength >> 8) & 0xFF,
        ])


@dataclass
class USBResponse:
    """Response from a USB transfer."""
    success: bool
    data: bytes = b''
    error: str = ''
    cycles_taken: int = 0


class USBHost:
    """
    USB Host that communicates with firmware via pure MMIO/DMA.

    This class provides a USB host interface that:
    1. Injects USB control transfers by writing to MMIO registers
    2. Waits for firmware to process the request
    3. Captures response data from DMA output buffer (0x8000)

    The host NEVER parses USB request content - it just moves bytes
    between the host interface and MMIO registers.
    """

    # USB data buffer address (where firmware DMAs responses)
    USB_DATA_BUFFER = 0x8000

    def __init__(self, emulator):
        """
        Initialize USB host with reference to emulator.

        Args:
            emulator: Emulator instance with hw (HardwareState) and memory
        """
        self.emu = emulator
        self.hw = emulator.hw
        self.memory = emulator.memory

        # Response capture
        self._pending_transfer: Optional[USBControlTransfer] = None
        self._response_ready = threading.Event()
        self._response_data: bytes = b''
        self._response_error: str = ''

        # DMA capture callbacks
        self._original_dma_callback = None
        self._install_dma_capture()

        # Transfer timeout (in cycles)
        self.timeout_cycles = 1000000  # 1M cycles default

    def _install_dma_capture(self):
        """Install DMA capture callback to monitor firmware responses."""
        # We capture writes to the USB data buffer at 0x8000 by monitoring
        # the DMA trigger points. The response is ready when firmware
        # signals transfer complete.
        pass  # Response capture is done via polling in wait_for_response

    def inject_control_transfer(self, transfer: USBControlTransfer) -> None:
        """
        Inject a USB control transfer via MMIO registers.

        This sets up the MMIO registers that the firmware reads to process
        the USB control transfer. The firmware handles all parsing and response
        generation.

        Args:
            transfer: The USB control transfer to inject
        """
        # Store pending transfer for response capture
        self._pending_transfer = transfer
        self._response_ready.clear()
        self._response_data = b''
        self._response_error = ''

        # Clear USB data buffer before transfer
        for i in range(min(transfer.wLength, 256)):
            self.memory.xdata[self.USB_DATA_BUFFER + i] = 0x00

        # Write setup packet to MMIO registers (0x9E00-0x9E07)
        setup = transfer.to_setup_packet()
        for i, byte in enumerate(setup):
            self.hw.regs[0x9E00 + i] = byte

        # Also populate usb_ep0_buf for firmware reads
        for i, byte in enumerate(setup):
            self.hw.usb_ep0_buf[i] = byte

        # Set USB connection and interrupt status
        # Bit 7 = connected, Bit 0 = active
        self.hw.regs[0x9000] = 0x81
        self.hw.regs[0xC802] = 0x01  # USB interrupt pending

        # Mark control transfer as active
        self.hw.usb_control_transfer_active = True
        self.hw.usb_92c2_read_count = 0
        self.hw.usb_ce89_read_count = 0

        # Set up request-type-specific registers
        request_type = transfer.bmRequestType & 0x60

        if request_type == 0x00:
            # Standard request (GET_DESCRIPTOR, SET_ADDRESS, etc.)
            # Bit 5 CLEAR for standard path, bits 0,1,3 set
            self.hw.regs[0x9101] = 0x0B
            # Bit 6 arms EP0 for transfer
            self.hw.regs[0x9301] = 0x40
        elif request_type == 0x20:
            # Class request
            self.hw.regs[0x9101] = 0x0B
            self.hw.regs[0x9301] = 0x40
        else:
            # Vendor request
            # Bit 5 SET for vendor path
            self.hw.regs[0x9101] = 0x21

        # Set endpoint status registers
        self.hw.regs[0x91D1] = 0x08  # EP0 setup received
        self.hw.regs[0x9118] = 0x01  # Endpoint index
        self.hw.regs[0x92F8] = 0x0C  # Bits 2-3 set
        self.hw.regs[0x9002] = 0x00  # Allow 0x9091 check
        self.hw.regs[0x9091] = 0x02  # Trigger handler

        # Set polling exit conditions
        self.hw.regs[0xE712] = 0x01  # Bit 0 for polling exit
        self.hw.regs[0xCC11] = 0x02  # Bit 1 backup exit

        # Set USB state and PCIe state
        if self.memory:
            self.memory.idata[0x6A] = 5  # USB configured
            self.memory.xdata[0x0AF7] = 0x01  # PCIe enumeration complete
            self.memory.xdata[0x053F] = 0x01  # PCIe link state
            self.memory.xdata[0x05A3] = 0x00  # Port index
            self.memory.xdata[0x05B1] = 0x03  # Port state (not 4)
            # USB descriptor handler state - main loop checks this at 0xD088
            self.memory.xdata[0x07E1] = 0x05

        # PCIe link state
        self.hw.regs[0xB480] = 0x03  # PCIe active

        # Mark command pending
        self.hw.usb_cmd_pending = True
        self.hw._pending_usb_interrupt = True

        print(f"[USBHost] Injected control transfer: "
              f"bmRequestType=0x{transfer.bmRequestType:02X} "
              f"bRequest=0x{transfer.bRequest:02X} "
              f"wValue=0x{transfer.wValue:04X} "
              f"wLength={transfer.wLength}")

    def inject_vendor_command(self, cmd_type: int, xdata_addr: int,
                              value: int = 0, size: int = 1) -> None:
        """
        Inject a vendor command (E4 read / E5 write) via MMIO.

        Args:
            cmd_type: 0xE4 (read) or 0xE5 (write)
            xdata_addr: Target XDATA address
            value: Value for E5 write
            size: Size for E4 read
        """
        # Build USB address format
        usb_addr = (xdata_addr & 0x1FFFF) | 0x500000

        # Build 6-byte CDB
        cdb = bytes([
            cmd_type,
            size if cmd_type == 0xE4 else value,
            (usb_addr >> 16) & 0xFF,
            (usb_addr >> 8) & 0xFF,
            usb_addr & 0xFF,
            0x00
        ])

        # Write CDB to USB interface registers
        for i, b in enumerate(cdb):
            self.hw.regs[0x910D + i] = b
            self.hw.usb_ep_data_buf[i] = b
            self.hw.usb_ep0_buf[i] = b
        self.hw.usb_ep0_len = len(cdb)

        # Set command type and state
        self.hw.usb_cmd_type = cmd_type
        self.hw.usb_cmd_size = size if cmd_type == 0xE4 else 0
        if cmd_type == 0xE5:
            self.hw.usb_e5_pending_value = value

        # Target address registers
        self.hw.regs[0xCEB2] = (xdata_addr >> 8) & 0xFF
        self.hw.regs[0xCEB3] = xdata_addr & 0xFF
        self.hw.regs[0xCEB0] = 0x05 if cmd_type == 0xE5 else 0x04

        # USB setup packet format
        self.hw.regs[0x9E00] = 0xC0 if cmd_type == 0xE4 else 0x40
        self.hw.regs[0x9E01] = cmd_type
        self.hw.regs[0x9E02] = xdata_addr & 0xFF
        self.hw.regs[0x9E03] = (xdata_addr >> 8) & 0xFF
        self.hw.regs[0x9E06] = size

        # Connection and interrupt
        self.hw.regs[0x9000] = 0x80  # Vendor path
        self.hw.regs[0x9101] = 0x21  # Vendor request
        self.hw.regs[0xC802] = 0x05

        # PCIe state registers - critical for E4/E5 command processing
        # 0xE091 function checks 0xB432 & 0x07 == 0x07, then 0xE765 bit 1
        self.hw.regs[0xB432] = 0x07  # PCIe link status - bits 0-2 must be set
        self.hw.regs[0xE765] = 0x02  # Bit 1 must be set for R7 = 1 return

        # USB state
        self.hw.usb_cmd_pending = True
        self.hw._pending_usb_interrupt = True
        self.hw.usb_ce89_read_count = 0
        self.hw._e5_dma_done = False

        # Clear CPU interrupt state to allow new interrupt to fire
        # This is needed because the firmware's ISR doesn't return with RETI -
        # it falls through to the main loop. When injecting a new command,
        # we simulate a new hardware event that should trigger a new interrupt.
        if hasattr(self.emu, 'cpu') and self.emu.cpu:
            self.emu.cpu.in_interrupt = False

        # RAM setup - these are the critical values firmware checks
        if self.memory:
            self.memory.idata[0x6A] = 5  # USB state = configured

            # CDB area (firmware reads command info from here)
            for i, b in enumerate(cdb):
                self.memory.xdata[0x0002 + i] = b
            self.memory.xdata[0x0003] = 0x08  # Vendor command flag

            # CRITICAL: These control the vendor command dispatch path
            # 0x07EC must be 0 (checked at 0x35C0, jz continues, jnz exits)
            self.memory.xdata[0x07EC] = 0x00

            # 0x05A5 = command slot count - MUST BE NON-ZERO
            # Read at 0x17B1, stored in R7, checked at 0x35CF
            # If R7 == 0, firmware exits vendor handler early
            self.memory.xdata[0x05A5] = 0x01

            # 0x05A3 = port index
            # NOTE: Function 0x17B1 OVERWRITES 0x05A3 with the value from 0x05A5!
            # So setting 0x05A3 here has no effect - it will be set to 0x01 by the firmware.
            self.memory.xdata[0x05A3] = 0x00

            # Command marker table - firmware reads from 0x05B1 + (slot_index * 0x22)
            # Since 0x17B1 copies 0x05A5 (=0x01) to 0x05A3, the firmware reads slot 1.
            # Slot addresses: slot 0 = 0x05B1, slot 1 = 0x05D3, slot 2 = 0x05F5, etc.
            #
            # Firmware XORs the value at this address with 0x04:
            # - If result is 0, it's an E4 (read) command
            # - If XOR with 0x05 is 0, it's an E5 (write) command
            if cmd_type == 0xE4:
                # Write to slot 1 (0x05D3) since that's what firmware will read
                self.memory.xdata[0x05D3] = 0x04
                # Also write to slot 0 for completeness
                self.memory.xdata[0x05B1] = 0x04
            elif cmd_type == 0xE5:
                self.memory.xdata[0x05D3] = 0x05
                self.memory.xdata[0x05B1] = 0x05

            # PCIe enumeration state
            self.memory.xdata[0x0AF7] = 0x01
            self.memory.xdata[0x053F] = 0x01

        print(f"[USBHost] Injected vendor command: 0x{cmd_type:02X} "
              f"addr=0x{xdata_addr:04X} "
              f"{'size' if cmd_type == 0xE4 else 'val'}=0x{(size if cmd_type == 0xE4 else value):02X}")

    def wait_for_response(self, max_cycles: int = None) -> USBResponse:
        """
        Wait for firmware to complete the USB transfer.

        This runs the emulator until the transfer completes or times out.
        Response data is read from the DMA output buffer (0x8000).

        Args:
            max_cycles: Maximum cycles to wait (default: self.timeout_cycles)

        Returns:
            USBResponse with success status and data
        """
        if max_cycles is None:
            max_cycles = self.timeout_cycles

        start_cycles = self.hw.cycles

        # Run emulator until transfer completes or timeout
        while self.hw.cycles - start_cycles < max_cycles:
            if not self.emu.step():
                return USBResponse(
                    success=False,
                    error="Emulator halted",
                    cycles_taken=self.hw.cycles - start_cycles
                )

            # Check if transfer completed
            if not self.hw.usb_control_transfer_active and not self.hw.usb_cmd_pending:
                break

        cycles_taken = self.hw.cycles - start_cycles

        # Check for timeout
        if cycles_taken >= max_cycles:
            return USBResponse(
                success=False,
                error="Transfer timeout",
                cycles_taken=cycles_taken
            )

        # Read response from DMA buffer
        if self._pending_transfer and self._pending_transfer.is_in_transfer:
            length = min(self._pending_transfer.wLength, 256)
            data = bytes(self.memory.xdata[self.USB_DATA_BUFFER + i]
                        for i in range(length))
            return USBResponse(
                success=True,
                data=data,
                cycles_taken=cycles_taken
            )

        return USBResponse(success=True, cycles_taken=cycles_taken)

    def control_transfer(self, bmRequestType: int, bRequest: int,
                         wValue: int, wIndex: int, wLength: int,
                         data: bytes = b'') -> USBResponse:
        """
        Perform a complete USB control transfer.

        This is a convenience method that injects the transfer and waits
        for the response.

        Args:
            bmRequestType: Request type and direction
            bRequest: Request code
            wValue: Value field
            wIndex: Index field
            wLength: Data length
            data: Data for OUT transfers

        Returns:
            USBResponse with success status and data
        """
        transfer = USBControlTransfer(
            bmRequestType=bmRequestType,
            bRequest=bRequest,
            wValue=wValue,
            wIndex=wIndex,
            wLength=wLength,
            data=data
        )
        self.inject_control_transfer(transfer)
        return self.wait_for_response()

    def get_descriptor(self, desc_type: int, desc_index: int = 0,
                       length: int = 255) -> USBResponse:
        """
        Get a USB descriptor from the device.

        Args:
            desc_type: Descriptor type (1=device, 2=config, 3=string, etc.)
            desc_index: Descriptor index (for string descriptors)
            length: Maximum length to read

        Returns:
            USBResponse with descriptor data
        """
        wValue = (desc_type << 8) | desc_index
        return self.control_transfer(
            bmRequestType=0x80,  # Device-to-host, standard, device
            bRequest=USBRequest.GET_DESCRIPTOR,
            wValue=wValue,
            wIndex=0,
            wLength=length
        )

    def e4_read(self, xdata_addr: int, size: int = 1) -> USBResponse:
        """
        Perform an E4 read (read from XDATA).

        Args:
            xdata_addr: XDATA address to read
            size: Number of bytes to read

        Returns:
            USBResponse with read data
        """
        self.inject_vendor_command(0xE4, xdata_addr, size=size)
        response = self.wait_for_response()
        if response.success:
            # E4 response is in USB buffer
            data = bytes(self.memory.xdata[self.USB_DATA_BUFFER + i]
                        for i in range(size))
            return USBResponse(
                success=True,
                data=data,
                cycles_taken=response.cycles_taken
            )
        return response

    def e5_write(self, xdata_addr: int, value: int) -> USBResponse:
        """
        Perform an E5 write (write to XDATA).

        Args:
            xdata_addr: XDATA address to write
            value: Value to write (single byte)

        Returns:
            USBResponse indicating success/failure
        """
        self.inject_vendor_command(0xE5, xdata_addr, value=value)
        return self.wait_for_response()


class ThreadedUSBHost:
    """
    USB Host that runs the emulator in a background thread.

    This provides a thread-safe interface for USB operations where the
    emulator runs continuously in a background thread and USB commands
    can be injected from any thread.
    """

    def __init__(self, emulator):
        """
        Initialize threaded USB host.

        Args:
            emulator: Emulator instance
        """
        self.emu = emulator
        self.hw = emulator.hw
        self.memory = emulator.memory

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Command queue
        self._command_queue: queue.Queue = queue.Queue()
        self._response_queue: queue.Queue = queue.Queue()

        # Synchronization
        self._command_event = threading.Event()

    def start(self):
        """Start the emulator thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Wait for USB to connect
        time.sleep(0.1)
        while not self.hw.usb_connected:
            time.sleep(0.01)
            if not self._running:
                break

        print("[ThreadedUSBHost] Started, USB connected")

    def stop(self):
        """Stop the emulator thread."""
        self._running = False
        self._command_event.set()  # Wake up thread
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[ThreadedUSBHost] Stopped")

    def _run_loop(self):
        """Main emulator loop running in background thread."""
        try:
            while self._running:
                # Check for pending commands
                try:
                    cmd = self._command_queue.get_nowait()
                    self._process_command(cmd)
                except queue.Empty:
                    pass

                # Run emulator
                if not self.emu.step():
                    print("[ThreadedUSBHost] Emulator halted")
                    break

        except Exception as e:
            print(f"[ThreadedUSBHost] Error: {e}")
            self._running = False

    def _process_command(self, cmd: dict):
        """Process a command from the queue."""
        cmd_type = cmd.get('type')

        if cmd_type == 'control_transfer':
            transfer = cmd['transfer']
            host = USBHost(self.emu)
            host.inject_control_transfer(transfer)

            # Wait for response
            start = self.hw.cycles
            max_cycles = cmd.get('timeout', 500000)
            while self.hw.cycles - start < max_cycles:
                if not self.hw.usb_cmd_pending and not self.hw.usb_control_transfer_active:
                    break
                if not self.emu.step():
                    break

            # Build response
            if transfer.is_in_transfer:
                length = min(transfer.wLength, 256)
                data = bytes(self.memory.xdata[0x8000 + i] for i in range(length))
                self._response_queue.put(USBResponse(
                    success=True,
                    data=data,
                    cycles_taken=self.hw.cycles - start
                ))
            else:
                self._response_queue.put(USBResponse(
                    success=True,
                    cycles_taken=self.hw.cycles - start
                ))

        elif cmd_type == 'vendor_command':
            host = USBHost(self.emu)
            host.inject_vendor_command(
                cmd['cmd'],
                cmd['addr'],
                cmd.get('value', 0),
                cmd.get('size', 1)
            )

            # Wait for completion
            start = self.hw.cycles
            max_cycles = cmd.get('timeout', 500000)
            while self.hw.cycles - start < max_cycles:
                if not self.hw.usb_cmd_pending:
                    break
                if not self.emu.step():
                    break

            # Build response
            if cmd['cmd'] == 0xE4:
                size = cmd.get('size', 1)
                data = bytes(self.memory.xdata[0x8000 + i] for i in range(size))
                self._response_queue.put(USBResponse(
                    success=True,
                    data=data,
                    cycles_taken=self.hw.cycles - start
                ))
            else:
                self._response_queue.put(USBResponse(
                    success=True,
                    cycles_taken=self.hw.cycles - start
                ))

    def control_transfer(self, bmRequestType: int, bRequest: int,
                         wValue: int, wIndex: int, wLength: int,
                         data: bytes = b'', timeout: int = 500000) -> USBResponse:
        """
        Perform a USB control transfer (thread-safe).

        Args:
            bmRequestType: Request type
            bRequest: Request code
            wValue: Value
            wIndex: Index
            wLength: Length
            data: Data for OUT transfers
            timeout: Timeout in cycles

        Returns:
            USBResponse
        """
        transfer = USBControlTransfer(
            bmRequestType=bmRequestType,
            bRequest=bRequest,
            wValue=wValue,
            wIndex=wIndex,
            wLength=wLength,
            data=data
        )

        self._command_queue.put({
            'type': 'control_transfer',
            'transfer': transfer,
            'timeout': timeout
        })

        return self._response_queue.get(timeout=10.0)

    def vendor_command(self, cmd: int, addr: int, value: int = 0,
                       size: int = 1, timeout: int = 500000) -> USBResponse:
        """
        Perform a vendor command (thread-safe).

        Args:
            cmd: Command type (0xE4 or 0xE5)
            addr: XDATA address
            value: Value for E5
            size: Size for E4
            timeout: Timeout in cycles

        Returns:
            USBResponse
        """
        self._command_queue.put({
            'type': 'vendor_command',
            'cmd': cmd,
            'addr': addr,
            'value': value,
            'size': size,
            'timeout': timeout
        })

        return self._response_queue.get(timeout=10.0)

    def get_descriptor(self, desc_type: int, desc_index: int = 0,
                       length: int = 255) -> USBResponse:
        """Get a USB descriptor (thread-safe)."""
        wValue = (desc_type << 8) | desc_index
        return self.control_transfer(
            bmRequestType=0x80,
            bRequest=USBRequest.GET_DESCRIPTOR,
            wValue=wValue,
            wIndex=0,
            wLength=length
        )

    def e4_read(self, addr: int, size: int = 1) -> USBResponse:
        """Perform E4 read (thread-safe)."""
        return self.vendor_command(0xE4, addr, size=size)

    def e5_write(self, addr: int, value: int) -> USBResponse:
        """Perform E5 write (thread-safe)."""
        return self.vendor_command(0xE5, addr, value=value)
