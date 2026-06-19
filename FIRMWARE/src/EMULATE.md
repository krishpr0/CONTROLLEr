Our goal is to get the emulation of the firmware running as an emulated USB device on the computer

- Emulator should run in its own thread. It should use the original firmware in fw.bin
- All communication with the emulator should be through MMIO
- It registers a dummy hcd SuperSpeed device, much be superspeed
- patch.py should work and have a model emulating the flash
- All descriptors are handled by logic in the firmware, NEVER HARDCODE ANY PIECE OF DESCRIPTORS
- All functions are handled by logic in the firmware
- The firmware runs in it's own thread and polling is done through MMIO
- There should be nothing parsing the commands in Python, the Python should just be a bridge
- The device should enumerate and show up in lsusb
- The device should show up as a mass storage device

## Current Status

### Working:
- Device enumeration (shows up in lsusb as 174c:2461)
- USB device descriptor handling via firmware DMA
- USB config descriptor with correct wTotalLength (121 bytes, includes both alt_settings)
- String descriptor handling
- Control transfers (GET_DESCRIPTOR, GET_MAX_LUN, BULK_ONLY_RESET)
- USB 2.0 High Speed mode (dummy_hcd only supports up to USB 2.0)

### Not Working:
- Bulk transfers (CBW/CSW for mass storage)
  - The bulk endpoint (0x02 OUT, 0x81 IN) is enabled but ep_read blocks
  - This may be a dummy_hcd limitation or a raw-gadget configuration issue
- UAS mode (requires USB 3.0 bulk streams, not supported by dummy_hcd)

### Known Limitations:
1. **dummy_hcd only supports USB 2.0 High Speed**
   - USB 3.0 SuperSpeed is not available
   - UAS mode requires USB 3.0 streams which are not supported
   - Device enumerates at High Speed, so USB 2.0 device descriptor is used

2. **Bulk transfers not functional**
   - The raw-gadget ep_read call blocks indefinitely waiting for data
   - Host-side libusb bulk transfers timeout with error -7
   - Control transfers work correctly, only bulk transfers are affected

## Running the Emulator

```bash
cd emulate
sudo modprobe dummy_hcd num=1
sudo modprobe raw_gadget
sudo python3 usb_device.py
```

The device will appear in lsusb:
```
Bus 005 Device XXX: ID 174c:2461 ASMedia Technology Inc. AS2462
```

## Testing

The test program `test_patch_usb.py` validates:
1. Device enumeration - PASS
2. Mass storage (BBB protocol) - FAIL (bulk transfers)
3. Vendor commands (E4/E5) - FAIL (requires bulk transfers)
4. String descriptors - PASS

Run with:
```bash
echo -n "5-1:1.0" | sudo tee /sys/bus/usb/drivers/usb-storage/unbind
sudo PYTHONPATH=/home/tiny/tinygrad python3 test_patch_usb.py
```
