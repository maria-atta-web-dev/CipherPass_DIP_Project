# Pakistan Bank KYC System — Viva Preparation Guide

## Important Questions and Answers

### Q1: "What is this project about?"
**Answer:**
"Yeh project bank KYC verification show karta hai for Pakistani CNIC. Isme hum CNIC image enhancement, face capture, criminal record check, aur duplicate fraud detection use karte hain. User CNIC front/back upload karta hai, face capture hota hai, system FIA watchlist aur internal criminal database check karta hai, phir approve/reject decision deta hai."

---

### Q2: "Real-life use case kya hai?"
**Answer:**
"Real life mein banks aur mobile wallets use karte hain yeh process. Jaise:
- branch account opening (HBL, UBL, Meezan)
- digital wallet signup (JazzCash, Easypaisa)
- microfinance loan verification
- FIA criminal screening

Yeh AML compliance ka bhi part hai. Bank ko customer identity verify karni hoti hai before account open karna."

---

### Q3: "Kaunse DIP techniques use kiye hain?"
**Answer:**
"Project mein hum ne multiple Digital Image Processing steps lagaye hain:
- Grayscale: color standardize karne ke liye
- Histogram Equalization: faded CNIC bright karne ke liye
- CLAHE: local contrast improve karne ke liye
- Gaussian Blur: camera noise kam karne ke liye
- Bilateral Filter: edges preserve karte hue smooth karne ke liye
- Edge Detection (Canny, Sobel, Laplacian): CNIC boundaries aur print edges detect karne ke liye
- Thresholding (Otsu, Adaptive): text/number ko binary banane ke liye
- Morphological operations: noise clean karne aur text structure maintain karne ke liye

Yeh sab important hai because mobile phone se li gayi poor quality image ko readable banana hota hai."

---

### Q4: "Image save ka feature kaise kaam karta hai?"
**Answer:**
"Jab aap `Show Image Processing Steps` pe click karte ho, har filter ek tile mein dikhta hai. Tile click karne se pop-up zoom open hota hai. Us pop-up mein `Save Filter Image` button hai. Agar aap save karoge, toh woh image `verification_data/cnic_archive/<CNIC>/` folder mein store hogi, aur uska path `archive.json` mein record hoga."

---

### Q5: "Criminal record check kaise kaam karta hai?"
**Answer:**
"System `criminal_records.json` mein check karta hai, jo FIA/AML watchlist simulate karta hai.

- Agar record high-risk hai, system auto-reject ya manual review suggest karega.
- Agar medium-risk hai, manual review hota hai.
- Agar clean hai, verification proceed karega.

Yeh check verification se pehle bhi popup me dikhta hai taaki teller ko immediately pata chal jaye."

---

### Q6: "Duplicate verification detect kaise hota hai?"
**Answer:**
"Har verification session `verification_data/history.json` mein save hota hai. Jab same CNIC phir se verify hota hai, hum previous count nikalte hain. Agar 3 ya zyada checks ho chuke hain, system duplicate fraud alert deta hai. Isse pata chal sakta hai ke koi same document repeatedly use kar raha hai."

---

### Q7: "Trust score ka formula kya hai?"
**Answer:**
"Trust score 3 parts se banta hai:

- Face Score 40%
- Document Score 35%
- Signature/other checks 25%

Phir penalties lagte hain:
- criminal record → -40
- reject decision → -25
- name mismatch → -35

Score >=70 = low risk, 45-69 = medium, <45 = high risk."

---

### Q8: "Compliance action kya hoti hai?"
**Answer:**
"Compliance dialog mein officer choose kar sakta hai:
- REJECT
- ESCALATE
- INVESTIGATE
- REPORT_FIA
- HOLD

`REPORT_FIA` ka matlab hai case FIA ko report karna. Yeh decision `verification_data/compliance_decisions.json` mein save hota hai."

---

### Q9: "System ka flow step-by-step batao."
**Answer:**
"Simple flow yeh hai:
1. CNIC front ya back upload karo
2. Customer details enter karo
3. Lookup profile se record check karo
4. Camera se face capture karo
5. Start verification pe click karo
6. System DIP apply karta hai, criminal database check karta hai, duplicate check karta hai, trust score nikalta hai
7. Agar criminal record mila, compliance review dialog open hota hai"

---

### Q10: "Koi demo CNIC examples batao."
**Answer:**
"Kuch important test CNICs:
- `42101-1234567-1` — clean record, approve expected
- `12345-6789012-3` — identity fraud + document forgery, criminal alert
- `11111-2222222-3` — money laundering, auto-reject
- `54321-0987654-1` — signature forgery, manual review

Agar same CNIC 3 baar verify karoge, duplicate alert bhi aayega."

---

### Q11: "Data kaha store hota hai?"
**Answer:**
"Data files:
- `citizen_database.json` — bank customer records
- `criminal_records.json` — criminal watchlist
- `verification_data/history.json` — KYC session history
- `verification_data/compliance_decisions.json` — officer decisions
- `verification_data/cnic_archive/<CNIC>/` — saved CNIC images aur filtered image archive

Yeh simple file-based storage hai, production mein real DB use hota."

---

## Short Hinglish Answers for Quick Recall

- "Yeh project Pakistani bank KYC process ko simulate karta hai with CNIC image processing aur AML screening."
- "Main feature ye hai ke filter images clickable hain, aur selected filter image ko archive mein save kar sakte hain."
- "Duplicate fraud tab detect hota hai jab ek hi CNIC 3 ya zyada baar verify ho chuka ho."
- "REPORT_FIA matlab agar criminal database strong match ho toh case FIA ko bhejne ka option."
- "Trust score face, document aur signature checks ke combination se nikalta hai."

---

## Quick Viva Demo Plan

1. **Show GUI** — "This is the Pakistan banking KYC terminal."
2. **Criminal Lookup** — enter `12345-6789012-3`, click lookup, show warning.
3. **Upload CNIC + DIP Steps** — upload front image, show all filters, click tile to zoom and save.
4. **Full verification** — capture face, start verification, show compliance review.
5. **Explain use** — "Banks use this for KYC and AML compliance."

---

## Key Files to Know

| File | What to Show |
|------|-------------|
| `main.py` | Main GUI and workflow |
| `cnic_archive.py` | Image archive save logic |
| `customer_screening.py` | Criminal check and duplicate detection |
| `dip_pipeline.py` | Image processing steps |
| `scoring.py` | Trust score formula |

---

## Common Teacher Questions

**Q: "Why warn before verification if criminal record found?"
A: "In real banking, teller ko pehle hi pata chalna chahiye agar CNIC FIA watchlist mein ho. Isse time bachta hai aur branch alert ho jati hai."

**Q: "Duplicate detection ka logic kya hai?"
A: "Har verification history mein save hoti hai. Jab same CNIC 3 baar se zyada verify hota hai, system duplicate alert deta hai. Yeh fraudster ka repeated attempt detect karta hai."

**Q: "Kya yeh production system hai?"
A: "Nahi, yeh educational prototype hai. Real banks actual government database aur advanced biometric system use karte hain. Yeh project concepts aur workflow sikhaata hai."

---

Good luck with your viva!
