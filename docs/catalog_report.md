# Catalog LCSC report (SCRUM-39, Sprint 2)

Date: 26 Nov 2026. Every part below was looked up on its LCSC product page (https://www.lcsc.com/product-detail/<C-number>.html). All are through-hole. Stock was checked on 26 Nov and may change.

Result: `python -m core.catalog_todo` shows **26/26 template parts ready**, plus 4 relay-driver parts, 13 resistor values; **all 5 examples (ac_9v, dual_rail, flasher, led_panel, relay) have an LCSC number on every BOM line.** `pytest`: 86 passed.

## Parts added

| Part key | LCSC | Manufacturer part | Package | Rating | Stock 26 Nov | Note |
|---|---|---|---|---|---|---|
| 1N5408 | C2460 | MDD 1N5408 | DO-201AD | 1000 V, 3 A | in stock | band = cathode |
| W04M | C22470848 | GOODWORK W04M | WOM | 400 V, 1.5 A | **out of stock** | alt in stock: Vishay W04G-E4/51 C145477 (check footprint) |
| KBP206 | C2494 | MDD KBP206 | KBP | 600 V, 2 A | in stock | + ~ ~ - (datasheet) |
| L7809CV | C8091 | ST L7809CV | TO-220 | 35 V in, 1.5 A | in stock | 1 IN, 2 GND, 3 OUT |
| L7812CV | C2914 | ST L7812CV-DG | TO-220 | 35 V in, 1.5 A | in stock | 1 IN, 2 GND, 3 OUT |
| POT-5K-RV09 | C42414342 | CTR R09711N0-FR20A13-B502-00Y | RV09 rotary, THT | 50 mW | 166 | alt trimmer 3296W-1-502 C118907 |
| POT-10K-RV09 | C42414336 | CTR R09710GS-FB15A7.0-B103-000 | RV09 rotary, THT | 50 mW | 192 | alt trimmer 3296W-1-103 C118954 |
| CAP-CER-100NF-50V | C254085 | Dersonic CC1H104MC1FD3F6C10MF | THT P=5.08 mm | 50 V | in stock | |
| CAP-CER-10NF-50V | C2761727 | Dersonic CC1H103ZC1ED3F4D1100 | THT P=5.08 mm | 50 V | in stock | +80/-20 % |
| LED-5MM-WHITE | C2895480 | XINGLIGHT XL-502UWC | 5 mm THT | 20 mA, Vf 3.3 V | in stock | |
| LED-3MM-GREEN | C2895476 | XINGLIGHT XL-302UGD | 3 mm THT | 20 mA, Vf 3.6 V | in stock | template assumes green Vf 2.1 V: check |
| CAP-ELEC-10UF-16V | C216302 | Huawei KF1C100MB050A00CV0 | Radial D4x5 mm | 16 V | in stock | |
| CAP-ELEC-100UF-50V | C134547 | Lelon RGA101M1HBKF-0811G | Radial D8x11.5 mm | 50 V | 310 | low stock |
| CAP-ELEC-470UF-25V | C43839 | Chengx KM477M025F12RR0VH2FP0 | Radial D8x12 mm | 25 V | in stock | |
| CAP-ELEC-1000UF-25V | C89783 | CapXon KF102M025G160A | Radial D10x16 mm | 25 V | in stock | |
| CAP-ELEC-2200UF-25V | C111500 | Rubycon 25YXJ2200M12.5X25 | Radial D12.5x25 mm | 25 V | in stock | |
| CAP-ELEC-4700UF-25V | C45070 | Chengx KM478M025K25RR0VH2FP0 | Radial D16x25 mm | 25 V | in stock | |
| RELAY-SRD-05VDC-SL-C | C35449 | Songle SRD-05VDC-SL-C | THT 19.2x15.6 mm, 5 pins | 10 A contacts | in stock | pin numbers: check EasyEDA footprint |
| RELAY-SRD-12VDC-SL-C | C30431 | Songle SRD-12VDC-SL-C | THT 19.2x15.6 mm, 5 pins | 10 A contacts | in stock | pin numbers: check EasyEDA footprint |
| PN2222A | C903217 | onsemi PN2222ATA | TO-92-3L | 40 V, 600 mA | in stock | 1 E, 2 B, 3 C (datasheet) |
| KF301-5.0-3P | C474882 | Cixi Kefa KF301-5.0-3P | THT 5.0 mm, 3P | 250 V, 17 A | in stock | |

## Resistors (Resistors sheet)

| Family | Value | LCSC | Manufacturer part |
|---|---|---|---|
| RES-0.25W | 120 | C1371058 | YAGEO MFR-25FTF52-120R |
| RES-0.25W | 240 | C58132 | UNI-ROYAL MFR0W4F2400A50 |
| RES-0.25W | 300 | C713985 | Huaxing MF1/4W-300R |
| RES-0.25W | 470 | C58592 | UNI-ROYAL MFR0W4F4700A50 (low stock) |
| RES-0.25W | 560 | C58635 | UNI-ROYAL MFR0W4F5600A50 |
| RES-0.25W | 820 | C2848612 | VO MF1/4W-820R |
| RES-0.25W | 1k | C713997 | Huaxing MF1/4W-1K |
| RES-0.25W | 1.3k | C2848597 | VO MF1/4W-1K3 |
| RES-0.25W | 1.8k | C58672 | UNI-ROYAL MFR0W4F1801A50 |
| RES-0.25W | 3.6k | C58655 | UNI-ROYAL MFR0W4F3601A50 |
| RES-0.25W | 10k | C57436 | UNI-ROYAL MFR0W4F1002A50 |
| RES-0.25W | 68k | C58630 | UNI-ROYAL MFR0W4F6802A50 |
| RES-1W | 470 | C172949 | YAGEO MFR1WSFTE52-470R |

## Still to check (acceptance criterion 3)

Pin **names** are standard for each package, but the pin **numbers** were not read from the EasyEDA symbols (LCSC pages show pinouts only as images). Before routing, check in EasyEDA (Place → Device → search the C-number): W04M, KBP206, both relays, PN2222A, the two pots. The builder's pin check (`compare_pins`) also stops the build on any mismatch.
