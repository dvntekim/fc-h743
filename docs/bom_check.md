# BOM availability check (JLCPCB parts library)

Queried JLCPCB's parts search API for every LCSC number in `fab/bom_jlc.csv` on 2026-10-31.
"base" parts carry no extended-part fee; "expand" parts add JLC's per-type fee. Stock moves daily: re-check on the order day.

| LCSC | MPN (JLC) | Qty on board | JLC stock | Library | Designators |
|---|---|---|---|---|---|
| C440198 | GRM21BR61H106KE43L | 4 | 1,337,551 | base | C1,C2,C6,C7 |
| C14663 | CC0603KRX7R9BB104 | 1 | 41,632,534 | base | C3 |
| C1525 | CL05B104KO5NNNC | 28 | 35,730,778 | base | C4,C5,C9,C13,C17,C18,C25,C27,C29,C30,C31,C32,C33,C34,C39,C40,C41,C44,C45,C47,C48,C49,C50,C53,C54,C56,C58,C60 |
| C45783 | CL21A226MAQNNNE | 4 | 3,756,082 | base | C10,C11,C12,C26 |
| C1538 | 0402B472K500NT | 4 | 1,062,764 | base | C14,C51,C57,C61 |
| C1567 | 0402CG470J500NT | 1 | 572,266 | base | C15 |
| C19702 | CL10A106KP8NNNC | 6 | 11,783,621 | base | C16,C19,C21,C22,C28,C52 |
| C32949 | CL05C100JB5NNNC | 1 | 2,422,336 | base | C20 |
| C52923 | CL05A105KA5NQNC | 6 | 10,259,800 | base | C23,C24,C38,C46,C55,C59 |
| C19666 | CL10A475KO8NNNC | 1 | 4,219,918 | base | C35 |
| C12530 | CL05A225MQ5NSNC | 2 | 3,841,277 | base | C36,C37 |
| C1547 | 0402CG120J500NT | 2 | 2,146,417 | base | C42,C43 |
| C43491 | BZT52C12 | 1 | 212,985 | expand | D1 |
| C113997 | SMBJ28A | 1 | 84,302 | expand | D2 |
| C94193 | B360A-13-F | 1 | 128,076 | expand | D3 |
| C2986059 | 19-217/GHC-YR1S2/6T | 1 | 691,004 | expand | D4 |
| C2286 | KT-0603R | 1 | 7,192,689 | base | D10 |
| C965807 | XL-1608UBC-04 | 1 | 2,407,261 | expand | D11 |
| C2986059 | 19-217/GHC-YR1S2/6T | 1 | 691,004 | expand | D12 |
| C8598 | B5819W SL | 1 | 690,843 | base | D20 |
| C69688 | nSMD050 | 1 | 15,992 | expand | F1 |
| C76885 | BLM15AX221SN1D | 1 | 66,013 | expand | FB1 |
| C165948 | TYPE-C-31-M-12 | 1 | 380,295 | expand | J20 |
| C114218 | DM3AT-SF-PEJM5 | 1 | 19,222 | expand | J21 |
| C189895 | SM04B-GHS-TB(LF)(SN) | 1 | 24,700 | expand | J30 |
| C189895 | SM04B-GHS-TB(LF)(SN) | 1 | 24,700 | expand | J31 |
| C133065 | SM06B-GHS-TB(LF)(SN) | 1 | 24,634 | expand | J32 |
| C133065 | SM06B-GHS-TB(LF)(SN) | 1 | 24,634 | expand | J33 |
| C133065 | SM06B-GHS-TB(LF)(SN) | 1 | 24,634 | expand | J34 |
| C189895 | SM04B-GHS-TB(LF)(SN) | 1 | 24,700 | expand | J35 |
| C160407 | SM08B-SRSS-TB(LF)(SN) | 1 | 182,264 | expand | J36 |
| C56123098 | XY-SM06B-SRSS-TB | 1 | 6,394 | expand | J37 |
| C56123098 | XY-SM06B-SRSS-TB | 1 | 6,394 | expand | J38 |
| C177246 | FXL0530-4R7-M | 1 | 48,328 | expand | L1 |
| C98350 | WPN252012H2R2MT | 1 | 41,858 | expand | L2 |
| C7264680 | DMP4013LFGQ-13 | 1 | 3,358 | expand | Q1 |
| C20917 | AO3400A | 1 | 1,148,715 | base | Q2 |
| C8545 | 2N7002 | 1 | 3,402,819 | base | Q3 |
| C25741 | 0402WGF1003TCE | 9 | 8,293,023 | base | R1,R2,R11,R18,R19,R21,R24,R43,R74 |
| C25744 | 0402WGF1002TCE | 15 | 16,706,383 | base | R3,R9,R12,R13,R14,R15,R16,R22,R25,R27,R35,R36,R37,R38,R39 |
| C11702 | 0402WGF1001TCE | 3 | 21,475,957 | base | R4,R32,R68 |
| C64171 | 0402WGF1473TCE | 1 | 1,064 | expand | R5 |
| C43676 | 0402WGF3602TCE | 1 | 282,925 | expand | R6 |
| C54068 | 0402WGF1623TCE | 1 | 139,586 | expand | R7 |
| C26982 | 0402WGF5232TCE | 1 | 40,754 | expand | R8 |
| C11549 | 0402WGF9091TCE | 1 | 31,156 | expand | R10 |
| C27009 | 0402WGF4533TCE | 1 | 662,379 | expand | R17 |
| C25765 | 0402WGF2002TCE | 1 | 2,837,609 | base | R20 |
| C25768 | 0402WGF2202TCE | 2 | 1,185,810 | base | R23,R51 |
| C4109 | 0402WGF2001TCE | 1 | 10,732,199 | base | R26 |
| C25105 | 0402WGF330JTCE | 3 | 1,932,911 | base | R28,R29,R31 |
| C25092 | 0402WGF220JTCE | 1 | 2,857,849 | base | R30 |
| C25117 | 0402WGF4700TCE | 2 | 1,110,012 | base | R33,R34 |
| C25879 | 0402WGF2201TCE | 4 | 3,745,183 | base | R40,R41,R62,R63 |
| C25118 | 0402WGF470JTCE | 9 | 1,766,109 | expand | R42,R64,R65,R66,R67,R69,R70,R71,R72 |
| C17909 | 1206W4F1200T5E | 4 | 600,568 | base | R44,R45,R46,R47 |
| C25905 | 0402WGF5101TCE | 2 | 3,757,648 | base | R48,R49 |
| C26083 | 0402WGF1004TCE | 1 | 2,921,938 | base | R50 |
| C25779 | 0402WGF3302TCE | 1 | 2,430,334 | base | R52 |
| C25792 | 0402WGF4702TCE | 5 | 6,867,580 | base | R53,R54,R55,R56,R57 |
| C60310 | 0402WGF604JTCE | 4 | 176,146 | expand | R58,R59,R60,R61 |
| C25076 | 0402WGF1000TCE | 1 | 6,043,535 | base | R73 |
| C524806 | TPS54360BDDAR | 1 | 58,834 | expand | U1 |
| C2869734 | LM66100DCKR | 2 | 5,037 | expand | U2,U3 |
| C141836 | TLV62569DBVR | 1 | 304,849 | expand | U4 |
| C80670 | LP5907MFX-3.3/NOPB | 1 | 33,414 | expand | U5 |
| C55266 | TPS2553DBVR | 2 | 46,544 | expand | U6,U7 |
| C114409 | STM32H743VIT6 | 1 | 7,914 | expand | U10 |
| C22459454 | ICM-45686 | 1 | 5,307 | expand | U20 |
| C194919 | BMI088 | 1 | 9,518 | expand | U21 |
| C5362283 | BMP581 | 1 | 7,223 | expand | U22 |
| C7519 | USBLC6-2SC6 | 1 | 32,602 | expand | U30 |
| C5215833 | TCAN1462VDRBRQ1 | 2 | 11,257 | expand | U40,U41 |
| C138714 | TPD4E05U06DQAR | 1 | 130,755 | expand | U50 |
| C13738 | X322516MLB4SI | 1 | 360,110 | base | Y1 |

- 69 unique parts, 176 placements; every line in stock.
- 36 extended part types (fees apply).
- J1 (battery pads) and J39 (buzzer pads) are bare copper pads, not parts.
- Lowest stock lines: 0402WGF1473TCE 1,064, DMP4013LFGQ-13 3,358, LM66100DCKR 5,037, ICM-45686 5,307, XY-SM06B-SRSS-TB 6,394
