# Glossary of Terms

> **Healthcare Data and Web Scraping Terminology**

## Healthcare Terms

### NPI (National Provider Identifier)
A unique 10-digit identification number issued to healthcare providers in the United States by the Centers for Medicare and Medicaid Services (CMS). Every healthcare provider must have an NPI to submit claims.

**Example:** `1234567890`

### Provider
A healthcare professional or organization that delivers medical services. Can be:
- **Individual Provider**: A single practitioner (doctor, nurse, therapist)
- **Organization Provider**: A facility (hospital, clinic, pharmacy)

### Network
A group of healthcare providers contracted with an insurance company to provide services at negotiated rates. Common types:
- **PPO (Preferred Provider Organization)**: Flexible network with higher costs for out-of-network care
- **HMO (Health Maintenance Organization)**: Restricted network requiring referrals
- **EPO (Exclusive Provider Organization)**: In-network only except emergencies

### Specialty
The medical field a provider practices in. Examples:
- Family Medicine
- Internal Medicine
- Cardiology
- Orthopedic Surgery

### PCP (Primary Care Provider/Physician)
A healthcare provider who serves as the first point of contact for a patient. Often required for HMO plans.

### Accepting New Patients
Indicates whether a provider is currently accepting new patients. A key data point for network adequacy.

### Affiliation
A relationship between a provider and another entity:
- **Hospital Affiliation**: Hospitals where a provider has privileges
- **Group Affiliation**: Medical groups or practices a provider belongs to

---

## Insurance Coverage Types

### Medicare Advantage (MA)
Private health insurance plans approved by Medicare for people 65+ or with certain disabilities. Also known as Medicare Part C.

### Medicaid
Joint federal and state program providing health coverage for low-income individuals. Each state has its own Medicaid program.

### ACA (Affordable Care Act)
Health plans sold on the Health Insurance Marketplace, also known as "Obamacare" plans. Individual and family coverage.

### Large Group
Employer-sponsored health insurance for companies with 50+ employees.

---

## Platform Terms

### Healthsparq
A healthcare technology company providing provider directory solutions. Used by ~24 insurance carriers in this infrastructure. Requires browser automation for data extraction.

### Sapphire (ProviderFinderOnline)
A provider directory platform used by BCBS affiliates and other carriers. Standardized API structure across implementations.

### Anthem/Wellpoint
Large health insurance company infrastructure. Powers Anthem, Amerigroup, Healthy Blue, and Simply Healthcare brands.

### Werally
UnitedHealthcare's provider directory platform. Uses geographic grid-based search.

### Provider Lenz
A provider directory platform with anti-bot protection requiring CAPTCHA solving.

---

## Technical Terms

### Scraper
A program that automatically extracts data from websites or APIs.

### Pipeline
A series of processing steps that transform data from raw input to final output. In this system:
- **Phase 1**: Discovery/Search
- **Phase 2**: Detail Extraction
- **Phase 3**: Normalization

### JSONL (JSON Lines)
A file format where each line is a valid JSON object. Used for streaming large datasets.

**Example:**
```jsonl
{"npi": "1234567890", "name": "John Smith"}
{"npi": "0987654321", "name": "Jane Doe"}
```

### Deduplication
The process of removing duplicate records. In this system, deduplication is NPI-based - records with the same NPI are merged.

### Normalization
The process of transforming data into a standard format. Converts diverse API responses into consistent output schema.

### Rate Limiting
Restrictions on how many requests can be made to an API in a time period. Common limits:
- 429 Too Many Requests
- X-RateLimit-Remaining header

### Stealth Browser
A browser configured to avoid bot detection. Uses techniques like:
- Hiding WebDriver flag
- Randomizing fingerprints
- Rotating User-Agents

### Proxy
An intermediate server that forwards requests on behalf of the client. Used to:
- Rotate IP addresses
- Bypass geographic restrictions
- Avoid IP-based blocking

### VPN (Virtual Private Network)
Encrypted connection to a remote server that masks the client's IP address. Used for anonymity and avoiding detection.

### CAPTCHA
"Completely Automated Public Turing test to tell Computers and Humans Apart" - challenges designed to block bots.

---

## API Terms

### REST (Representational State Transfer)
An architectural style for web services using HTTP methods (GET, POST, PUT, DELETE).

### Endpoint
A specific URL that an API exposes for accessing resources.

**Example:** `https://api.example.com/v1/providers`

### Pagination
Splitting large result sets into smaller pages. Common patterns:
- Page number: `?page=1&limit=100`
- Offset: `?offset=0&limit=100`
- Cursor: `?cursor=abc123`

### Header
Metadata sent with HTTP requests/responses. Common examples:
- `Authorization: Bearer token`
- `Content-Type: application/json`
- `X-API-Key: your-key`

---

## File Formats

### JSON (JavaScript Object Notation)
A lightweight data interchange format.
```json
{"key": "value", "array": [1, 2, 3]}
```

### JSONL (JSON Lines)
One JSON object per line.
```jsonl
{"id": 1}
{"id": 2}
```

### 7z
A compressed archive format with high compression ratio. Used for output packaging.

---

## Configuration Terms

### PREV_DATE / CURR_DATE
Date stamps in YYYYMMDD format indicating:
- **PREV_DATE**: Previous scraping run (for comparison)
- **CURR_DATE**: Current scraping run

### Network ID
Carrier-specific identifier for a network plan. Used to filter providers.

### Geographic Coordinates
Latitude/longitude pairs used for location-based searches.
- **Latitude**: North-South position (-90 to 90)
- **Longitude**: East-West position (-180 to 180)
- **Radius**: Search area in miles

---

## Common Abbreviations

| Abbreviation | Full Term |
|--------------|-----------|
| API | Application Programming Interface |
| BCBS | Blue Cross Blue Shield |
| CMS | Centers for Medicare & Medicaid Services |
| ETL | Extract, Transform, Load |
| HIPAA | Health Insurance Portability and Accountability Act |
| HTTP | HyperText Transfer Protocol |
| IP | Internet Protocol |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| NPI | National Provider Identifier |
| PCP | Primary Care Provider |
| PPO | Preferred Provider Organization |
| QA | Quality Assurance |
| REST | Representational State Transfer |
| SSL | Secure Sockets Layer |
| TLS | Transport Layer Security |
| UHC | UnitedHealthcare |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |
| VPN | Virtual Private Network |

---

*Last Updated: December 2024*
