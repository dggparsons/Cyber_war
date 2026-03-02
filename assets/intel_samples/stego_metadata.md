# Intel Drop: Metadata Steganography

**Puzzle Type:** Steganography
**Difficulty:** Medium-Hard
**Category:** Digital Forensics / Metadata Analysis

---

## CLASSIFIED -- DIGITAL FORENSICS REPORT

**From:** Cyber Forensics Lab -- Evidence Processing Unit
**To:** Joint Cyber Command, Counterintelligence Division
**Priority:** IMMEDIATE

Our digital forensics team seized a laptop from a suspected IRONVEIL
operative during a border crossing operation. Among thousands of
innocuous tourist photographs, one image file had anomalous EXIF
metadata that does not match the camera's standard output. The full
metadata dump from `IMG_20260215_091337.jpg` is reproduced below.

### Extracted Metadata (exiftool output)

```
======== IMG_20260215_091337.jpg ========
ExifTool Version Number         : 12.76
File Name                       : IMG_20260215_091337.jpg
File Size                       : 4.2 MB
File Type                       : JPEG
MIME Type                       : image/jpeg
Image Width                     : 4032
Image Height                    : 3024
Bits Per Sample                 : 8
Color Space                     : sRGB
Compression                     : JPEG (old-style)
Make                            : Samsung
Camera Model Name               : SM-S918B
Lens Model                      : Samsung S5KGN2 f/1.7
Orientation                     : Horizontal (normal)
X Resolution                    : 72
Y Resolution                    : 72
Resolution Unit                 : inches
Software                        : G918BXXS7DXAA
Date/Time Original              : 2026:02:15 09:13:37
Create Date                     : 2026:02:15 09:13:37
Modify Date                     : 2026:02:15 09:13:37
Exposure Time                   : 1/250
F Number                        : 1.7
ISO                             : 50
Focal Length                    : 6.4 mm
Flash                           : No Flash
Metering Mode                   : Multi-segment
White Balance                   : Auto
Digital Zoom Ratio              : 1
Scene Capture Type              : Standard
GPS Latitude                    : 48 deg 51' 23.81" N
GPS Longitude                   : 2 deg 21' 07.00" E
GPS Altitude                    : 35.2 m
Artist                          : 455846494C5452415445
Copyright                       :
User Comment                    : Processed by GIMP 2.10
XMP Toolkit                     : Adobe XMP Core 5.6-c140
Description                     : Holiday photo - Eiffel Tower
Subject                         : travel, paris, vacation
Creator Tool                    : Samsung Camera v12.1
Thumbnail Offset                : 1024
Thumbnail Length                : 7849
```

### Analyst Notes

- Most metadata fields are consistent with a Samsung Galaxy S24 Ultra
  photograph taken near the Eiffel Tower (GPS coordinates: 48.856N, 2.352E).
- The **Artist** field is anomalous: `455846494C5452415445` does not
  match any photographer name or Samsung default value.
- The Artist field value appears to be a **hex-encoded ASCII string**.
- Samsung phones do not populate the Artist EXIF field by default.
- The User Comment field referencing GIMP suggests post-processing,
  which could be when the covert data was inserted.

### Hints (reveal progressively if team is stuck)

1. **Hint 1:** Focus on the metadata field that looks different from the others. Most fields contain readable English or standard camera values.
2. **Hint 2:** The Artist field contains `455846494C5452415445`. This is hexadecimal -- each pair of characters represents one ASCII byte.
3. **Hint 3:** Decode the hex pairs: `45`=E, `58`=X, `46`=F, `49`=I, `4C`=L, `54`=T, `52`=R, `41`=A, `54`=T, `45`=E.

---

## GM SOLUTION

**Answer:** `EXFILTRATE`

**Walkthrough:**

The hidden message is in the **Artist** EXIF field. The value
`455846494C5452415445` is a hex-encoded ASCII string:

```
45 = E
58 = X
46 = F
49 = I
4C = L
54 = T
52 = R
41 = A
54 = T
45 = E
```

Decoded: **EXFILTRATE**

Verification (Python):
```python
import binascii
binascii.unhexlify("455846494C5452415445").decode()
# -> 'EXFILTRATE'
```

**SHA-256 hash of solution:**
`555d7beab82ae9575640f99cb61e8ceb6ac1439f214e62d31a3ef83a2d8a3f7a`

### GM Setup -- API Call

```json
{
  "puzzle_type": "steganography",
  "clue": "Seized laptop image IMG_20260215_091337.jpg has anomalous EXIF Artist field: 455846494C5452415445 -- all other metadata appears normal. Decode the hidden message.",
  "solution": "EXFILTRATE",
  "reward_type": "false_flag"
}
```
