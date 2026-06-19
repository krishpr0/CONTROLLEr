# CONTROLLER

CONTROLLER, IT is an Circuit which allows any type of SSD/HDD of a laptop size which is 2.5 inch Memory be a External Storage. This Project main chip is the ASM2464PD due to its high speed transfer speed. This chip was selected due to its support of USB4/Thunderbolt.

<img width="420" height="595" alt="ZINE" src="https://github.com/user-attachments/assets/1683ffbf-d227-49b5-81af-28af350c3fa5" />




## What is this Project?
Controller is a high speed transfer external circuit board which is meant to make any 2.5 inch hard drive or ssd into an external Storage system. This unlocks the ability to make our own external storage system rather then buying it from outside. 


## How do we use Controller?
- First of all there are 4 screws on the side 2 on each unscrew it!
- Then pull of the top cover off the base plate.
- Then insert and slide in the HDD/SSD onto the PCIe connector.
- Place the cover plate back on and then tighten the screw 2 on each side this should secure the storage as well as the top case.
- Then connect to the computer that's it!
- (*NOTE: SOME MAY REQUIRE TO FLASH A FIRMWARE*)


## The reason for building this
Nowadays the software programs are increasing in size and as the phoots, videos we click also getting bigger and bigger. In my case each of my photos clicked is more than 5MB so that storage would rlly quickly fill up and I had to either delete it or buy an external drive and store it there.!

And so I choose the 2nd opt buy and external drive to store it cuz why delete photos which is memoory.!
So yeh like that it went on for years and years pile of drives js filled with photos, videos and files but now the storage are getting more expensier and also the casing used to hold the drive. !

SO i was really frustraied atp And i thought abt is there a way to make a good external drive !?
SO that was the reason i started this project due to the rise in price of storage due to AI>
T-T


## CAD
<img width="1920" height="692" alt="CASE" src="https://github.com/user-attachments/assets/57645ba1-4479-4269-af10-f7ee58254f2f" />
<img width="1920" height="692" alt="!@45" src="https://github.com/user-attachments/assets/2193563e-bf6a-4108-be75-7fbef4e3e048" />
<img width="1920" height="692" alt="!)(@" src="https://github.com/user-attachments/assets/ba0df2d1-9425-4397-9b78-2f087401fb17" />


## CIRCUIT DIAGRAM: 
<img width="732" height="522" alt="Screenshot 2026-06-17 125731" src="https://github.com/user-attachments/assets/1921ce5d-3e7e-4565-967d-90b0c1b22f5d" />


<img width="647" height="341" alt="Screenshot 2026-06-17 125722" src="https://github.com/user-attachments/assets/a466ca37-c2a3-4355-83a5-bb9feeb8a6ec" />

<img width="1002" height="606" alt="Screenshot 2026-06-17 134327" src="https://github.com/user-attachments/assets/5a3e9f7f-2971-4c66-aef8-4198b6a9de09" />


<img width="907" height="452" alt="Screenshot 2026-06-17 215047" src="https://github.com/user-attachments/assets/9d992e9c-294d-43fa-b627-94016ffb50cf" />


<img width="907" height="452" alt="Screenshot 2026-06-17 215047" src="https://github.com/user-attachments/assets/1656941c-013e-49b9-a2b4-991b46cf9d62" />

## PCB
<img width="610" height="335" alt="Screenshot 2026-06-18 172425" src="https://github.com/user-attachments/assets/859af080-3e8d-4447-aa26-1e6c68f86798" />

## PCB 3D
<img width="952" height="470" alt="Screenshot 2026-06-18 173036" src="https://github.com/user-attachments/assets/f3bad85a-7439-4351-8d6e-6268279de298" />



# BOM
| #  | Reference                             | Value                                    | Footprint                       | Qty | Unit (USD) | Total (USD) | Datasheet / Link                                                                              |
|----|---------------------------------------|------------------------------------------|---------------------------------|-----|------------|-------------|-----------------------------------------------------------------------------------------------|
| 1  | U1                                    | ASM2464PD  USB4 Host Controller          | ASM2464PD                       | 1   | $8.000     | $8.000      | https://www.asmedia.com.tw/product/aGaq3YfSP5Yrq0T0/cGaq7XeSw9YRQ5T1                          |
| 2  | U2                                    | SPI Flash  SOIC-8  (Firmware storage)    | SOIC-8_5.3x5.3mm_P1.27mm        | 1   | $3         | $3          | http://ww1.microchip.com/downloads/en/DeviceDoc/21832H.pdf                                    |
| 3  | U3                                    | SPI Flash  DFN-8  (Firmware storage)     | DFN-8-1EP_3x2mm_P0.5mm          | 1   | $3         | $3          | http://ww1.microchip.com/downloads/en/DeviceDoc/21832H.pdf                                    |
| 4  | Y1                                    | 25MHz Crystal  SMD 3225-4Pin             | Crystal_SMD_3225-4Pin_3.2x2.5mm | 1   | $0.350     | $0.350      | https://au.rs-online.com/web/p/crystal-units/9047531                                          |
| 5  | J1                                    | USB-C Receptacle  Amphenol 12401610E4-2A | USB_C_Receptacle_Amphenol       | 1   | $1.200     | $1.200      | https://www.usb.org/sites/default/files/documents/usb_type-c.zip                              |
| 6  | J2                                    | SPI Header  2x04  2.54mm                 | PinHeader_2x04                  | 1   | $0.100     | $0.100      | ---                                                                                           |
| 7  | J3                                    | PCIe x4 Connector  THT Open              | PCIe_x4_tht_open                | 1   | $1.500     | $1.500      | http://www.ritrontek.com/uploadfile/2016/1026/20161026105231124.pdf                           |
| 8  | J4                                    | Chip Annoyers Header  2x02  2.54mm       | PinHeader_2x02                  | 2   | $0.10      | $0.10       | https://www.digikey.com/en/products/detail/harwin-inc/M20-9990246/3728226                     |
| 9  | J5                                    | UART Header  1x04  2.54mm                | PinHeader_1x04                  | 1   | $0.10      | $0.050      | https://www.digikey.com/en/products/detail/jst-sales-america-inc/B4B-XH-A/1651047             |
| 10 | J6                                    | I2C Header  1x04  2.54mm                 | PinHeader_1x04                  | 1   | $0.10      | $0.050      | https://www.digikey.com/en/products/detail/jst-sales-america-inc/B4B-XH-A/1651047             |
| 11 | J7,J8,J9,J10                          | 1x06 Header  1.27mm  x4                  | PinHeader_1x06                  | 4   | $0.20      | $0.200      | https://www.digikey.in/en/products/detail/jst-sales-america-inc/B6B-PH-K-S/926615             |
| 12 | R1,R2,R20,R24,R26,R29,R39,R41,R42,R43 | 1k ohm  0402                             | R_0402_1005Metric               | 10  | $0.15      | $1.50       | https://www.digikey.com.au/en/products/detail/yageo/RC0402FR-071KL/726513                     |
| 13 | R3,R4,R5,R6,R7,R8,R25,R30,R31         | 0 ohm  0402                              | R_0402_1005Metric               | 9   | $0.15      | $1.35       | https://www.digikey.com.au/en/products/detail/yageo/RC0402JR-070RL/726406                     |
| 14 | R9,R27,R28,R35,R38,R34,R36,R37        | 4.7k ohm  0402                           | R_0402_1005Metric               | 8   | $0.15      | $0.75       | https://www.digikey.com.au/en/products/detail/yageo/RC0402JR-074K7L/726477                    |
| 15 | R10,R21,R22, R23                      | 10k ohm  0402                            | R_0201_0603Metric               | 4   | $0.15      | $0.60       | https://www.digikey.com.au/en/products/detail/vishay-dale/CRCW040210K0FKED/1178121            |
| 16 | R11,R12,R13,R14,R15,R16,R17,R18       | 220k ohm  0201                           | R_0201_0603Metric               | 8   | $0.15      | $1.20       | https://www.digikey.com/en/products/detail/yageo/RC0201JR-07220KP/15219948                    |
| 19 | R32                                   | 12.1k ohm  0402                          | R_0402_1005Metric               | 1   | $0.10      | $0.10       | https://www.digikey.in/en/products/detail/yageo/RC0402FR-1012K1L/17020868                     |
| 20 | R33                                   | 100k ohm  0402                           | R_0402_1005Metric               | 1   | $0.20      | $0.20       | https://www.digikey.com/en/products/detail/yageo/AT0402BRD07100KL/5138605                     |
| 22 | C1                                    | 10pF  0402                               | C_0402_1005Metric               | 1   | $0.10      | $0.10       | https://www.digikey.com/en/products/detail/yageo/CC0402JRNPO8BN100/5883266                    |
| 23 | C2,C3,C4,C5,C6,C7,C8,C9               | 330nF  0201                              | C_0201_0603Metric               | 8   | $0.10      | $0.80       | https://www.mouser.in/ProductDetail/Walsin/0201X334M6R3CT?qs=iLbezkQI%252Bsj6TtN1Mk8apQ%3D%3D |
| 24 | C10,C21                               | 1uF  0402                                | C_0402_1005Metric               | 2   | $0.01      | $0.02       | https://robu.in/product/1uf-capacitor-smdc-0402-pack-of-50/                                   |
| 25 | C11                                   | 220pF  0402  DNP                         | C_0402_1005Metric               | 1   | $0.10      | $0.10       | https://www.digikey.com/en/products/detail/yageo/CC0402GRNPO9BN221/5883253                    |
| 26 | C12,C13,C14,C15,C16,C17,C18,C19       | 220nF  0402                              | C_0402_1005Metric               | 8   | $0.003     | $0.024      | https://www.lcsc.com/product-detail/C2649521.html                                             |
| 27 | C20                                   | 100nF  0402                              | C_0402_1005Metric               | 1   | $0.003     | $0.003      | https://www.lcsc.com/product-detail/C60474.html                                               |
| 28 | D1,D2,D3,D4,D5,D6,D7,D8               | Diode  0201  DNP                         | D_0201_0603Metric               | 8   | $0.32      | $2.56       | https://www.digikey.in/en/products/detail/kyocera-avx/GG020105100N2P/6826542                  |
| 29 | D9,D10,D11,D12,D13,D14,D15,D16        | LED  0603                                | LED_0603_1608Metric             | 8   | $0.01      | $0.08       | https://www.lcsc.com/product-detail/C19171390.html                                            |
|    | TOTAL                                 |                                          |                                 |     |            | 15.462      |                                                                                               |



# HOW TO BUILD
<img width="732" height="522" alt="Screenshot 2026-06-17 125731" src="https://github.com/user-attachments/assets/1921ce5d-3e7e-4565-967d-90b0c1b22f5d" />


<img width="647" height="341" alt="Screenshot 2026-06-17 125722" src="https://github.com/user-attachments/assets/a466ca37-c2a3-4355-83a5-bb9feeb8a6ec" />

<img width="1002" height="606" alt="Screenshot 2026-06-17 134327" src="https://github.com/user-attachments/assets/5a3e9f7f-2971-4c66-aef8-4198b6a9de09" />


<img width="907" height="452" alt="Screenshot 2026-06-17 215047" src="https://github.com/user-attachments/assets/9d992e9c-294d-43fa-b627-94016ffb50cf" />


<img width="907" height="452" alt="Screenshot 2026-06-17 215047" src="https://github.com/user-attachments/assets/1656941c-013e-49b9-a2b4-991b46cf9d62" />

## What you need
-  Soldering Iron
-  Soldering wire
-  Flux
-  Multimeter
-  USB-C Cable

### Assembly Order
1. Solder all SMD Passives first (Resistors, Capacitors)
2. Solder ICs
3. Solder USB-C
4. Connect the PCIe Connecotr
5. Connect the Drive
6. Plug and Transfer.

### Firmware Setup 
- Open the 'firmware/src' - Upload the whole program to the SPI
- RUN

# Feature
- 1MB ROM
- SPI
- 40 GBPS USB Transfer Speed
- USB4/Thuerbolt Support
- HHD/SSD/NVMe support
- USB-C
- Power effiecent
