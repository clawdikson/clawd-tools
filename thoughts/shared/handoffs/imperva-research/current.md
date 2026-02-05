# Imperva Bot Protection Bypass Research

**Generated:** 2026-01-13
**Status:** Complete
**Context:** Web scraping with Camoufox + SmartProxy stack

---

## Summary

Imperva (formerly Incapsula) uses multi-layered detection including TLS fingerprinting (JA3/JA4), JavaScript challenges (reese84 cookie), behavioral analysis, and IP reputation scoring. Your current stack (Camoufox + SmartProxy residential proxies) is well-positioned for bypass, but requires specific configuration and behavioral patterns to succeed consistently.

---

## Questions Answered

### Q1: What fingerprinting techniques does Imperva use?

**Answer:** Imperva employs a multi-layered detection system:

1. **TLS Fingerprinting (JA3/JA4)**: Analyzes TLS handshake parameters to generate unique client fingerprints. JA4 is the newer, more granular successor.

2. **HTTP/2 Fingerprinting**: Detects subtle differences between HTTP/2 implementations of real browsers vs. automation tools.

3. **Device Fingerprinting**: Collects browser characteristics, plugins, screen resolution, WebGL, Canvas, AudioContext.

4. **reese84 Cookie Challenge**: Heavy fingerprint collection via obfuscated JavaScript. Generates encrypted payload with dozens of fingerprint data points encoded via xorshift128 algorithm.

5. **Behavioral Analysis**: Mouse movements, keystroke dynamics, navigation patterns, click sequences, scroll behavior.

6. **IP Reputation**: Cross-references IPs against known bot/malicious IP databases.

**Source:** [ScrapFly - Imperva Bypass Guide](https://scrapfly.io/blog/posts/how-to-bypass-imperva-incapsula-anti-scraping)
**Confidence:** High

### Q2: What are the known detection vectors?

**Answer:** Key detection vectors include:

| Vector | Detection Method | Mitigation |
|--------|-----------------|------------|
| TLS Fingerprint | JA3/JA4 hash mismatch | Use Camoufox (Firefox) or curl_cffi impersonation |
| CDP Protocol | Runtime.enable leak | Use Patchright (patches this) or Camoufox |
| navigator.webdriver | True in automation | Camoufox/Patchright mask this |
| Headless mode | Missing window features | Use virtual headless (Xvfb) |
| Request timing | Too fast/regular | Add randomized delays (2-7s) |
| Session patterns | Consistent fingerprint | Rotate fingerprints with sessions |
| IP reputation | Datacenter IPs | Use residential proxies (SmartProxy) |

**Source:** [ZenRows - Incapsula Bypass](https://www.zenrows.com/blog/incapsula-bypass)
**Confidence:** High

### Q3: How effective is Camoufox against Imperva?

**Answer:** Camoufox is one of the most effective open-source solutions for Imperva bypass:

**Strengths:**
- Native-level fingerprint spoofing (C++ injection, not JS patches)
- Firefox-based (less targeted than Chromium)
- BrowserForge integration for realistic fingerprint rotation
- Virtual headless mode (runs headful in Xvfb)
- Natural mouse movement algorithm
- WebGL, WebRTC, fonts, screen, audio context spoofing

**Limitations:**
- Open-source signature may be fingerprinted on high-traffic sites
- Requires manual CAPTCHA solving on first access (session persistence needed)
- Can be flagged after multiple session reuses
- May struggle with rapid anti-bot updates

**Source:** [ZenRows - Camoufox Guide](https://www.zenrows.com/blog/web-scraping-with-camoufox), [GitHub - daijro/camoufox](https://github.com/daijro/camoufox)
**Confidence:** High

### Q4: What role do residential proxies play?

**Answer:** Residential proxies are essential for Imperva bypass:

- **Datacenter IPs get blocked almost immediately** by Imperva
- Residential IPs mimic real user traffic and have better reputation
- SmartProxy session-based proxies maintain consistent IP for login flows
- Rotating proxies distribute load across many IPs

**SmartProxy Configuration Best Practices:**
- Use session-based for multi-request sessions (login flows)
- Session duration: 10-60 minutes recommended
- Distribute across 50+ IPs from different subnets
- Geo-targeting to match expected user location
- Rotate fingerprint when rotating proxy (never mid-session)

**Source:** [SmartProxy Best Practices](https://help.smartproxy.com/docs/best-scraping-practices-using-proxies)
**Confidence:** High

### Q5: How should request timing be handled?

**Answer:** Human-like timing is critical:

- **Base delay:** 2-7 seconds between requests (randomized)
- **Page load pause:** 3-10 seconds after navigation
- **Mouse movements:** Curved paths, not straight lines
- **Scroll behavior:** Gradual, random intermittent scrolling
- **Click timing:** Variable delays before/after clicks
- **Session duration:** 5-30 minutes of activity per session

**Anti-Pattern Detection:**
- Fixed intervals (e.g., exactly 2s between requests)
- No scrolling or mouse movement
- Instant page transitions
- Linear navigation patterns
- Too many requests per minute

**Source:** [ScrapingAnt - Human-Like Browsing Patterns](https://scrapingant.com/blog/human-like-browsing-patterns)
**Confidence:** High

---

## Detailed Findings

### Finding 1: Camoufox Configuration for Imperva

**Source:** [Camoufox Documentation](https://camoufox.com/python/usage/)

**Key Configuration Options:**

```python
from camoufox.async_api import AsyncCamoufox
from browserforge.fingerprints import Screen

async with AsyncCamoufox(
    # Operating system - match expected user demographics
    os=["windows", "macos"],  # or specific: "windows"
    
    # Screen constraints - match common resolutions
    screen=Screen(
        min_width=1280,
        max_width=1920,
        min_height=720,
        max_height=1080
    ),
    
    # Enable human-like mouse movements
    humanize=True,  # or max duration in seconds
    
    # Virtual headless (runs headful in Xvfb on Linux)
    headless="virtual",
    
    # Block WebRTC to prevent IP leaks
    block_webrtc=True,
    
    # Allow WebGL for fingerprint consistency
    allow_webgl=True,
    
    # Auto-calculate geo from proxy IP
    geoip=True,  # or pass specific IP
    
    # Proxy configuration
    proxy={
        "server": "http://gate.decodo.com:7000",
        "username": "user-session-abc123-sessionduration-10",
        "password": "password"
    }
) as browser:
    page = await browser.new_page()
    await page.goto("https://target-site.com")
```

**Best Practices:**
- Rotate fingerprints every 30-60 minutes or with proxy rotation
- Never change fingerprint mid-session on same proxy
- Use `geoip=True` to match timezone/locale to proxy location
- Consider custom fonts list matching target OS

### Finding 2: curl_cffi for HTTP-Level Bypass

**Source:** [curl_cffi Documentation](https://curl-cffi.readthedocs.io/en/v0.6.1/)

When sites don't require full browser execution (no reese84 challenge):

```python
from curl_cffi import requests

# Basic request with Chrome impersonation
response = requests.get(
    "https://target-site.com/api/data",
    impersonate="chrome131",  # Latest Chrome
    proxies={
        "http": "http://user:pass@gate.decodo.com:7000",
        "https": "http://user:pass@gate.decodo.com:7000"
    },
    headers={
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
)

# Session management for cookies
session = requests.Session()
session.impersonate = "chrome131"

# First request (may set cookies)
response = session.get("https://target-site.com")

# Subsequent requests with cookies
response = session.get("https://target-site.com/api/protected")
```

**Supported Browser Versions (2026):**
- `chrome131`, `chrome124`, `chrome123`, etc.
- `safari`, `safari_ios`
- Use `chrome` for latest version

**Limitation:** Cannot execute JavaScript challenges (reese84). Use for API endpoints after browser session establishes cookies.

### Finding 3: Patchright vs Camoufox

**Source:** [GitHub - patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright), [DEV.to Comparison](https://dev.to/claudeprime/patchright-vs-playwright-when-to-use-the-stealth-browser-fork-382a)

| Aspect | Patchright | Camoufox |
|--------|------------|----------|
| Engine | Chromium | Firefox |
| Anti-Detection Level | Medium | High |
| CDP Leak Fix | Yes (isolated contexts) | N/A (not CDP-based) |
| Fingerprint Rotation | Manual | Built-in (BrowserForge) |
| API Compatibility | Playwright drop-in | Playwright-compatible |
| Open Source Risk | Lower (less known) | Higher (well-known) |
| Best For | Sites with basic detection | Sites with advanced detection |

**Recommendation for Imperva:**
1. **Try Camoufox first** - highest anti-detection
2. **Fall back to Patchright** if Camoufox is fingerprinted
3. **Use curl_cffi** for API calls after session established

### Finding 4: reese84 Cookie Challenge

**Source:** [GitHub - BottingRocks/Incapsula](https://github.com/BottingRocks/Incapsula)

The reese84 challenge is Imperva's modern fingerprint collection system:

**How it works:**
1. Initial request returns JavaScript challenge
2. Browser executes obfuscated JS that collects 50+ fingerprint data points
3. Fingerprints encoded via xorshift128 algorithm
4. Payload sent to endpoint ending with `?d=site.com`
5. Server validates and sets `reese84` cookie
6. Cookie required for subsequent requests

**Key points:**
- **Cannot be bypassed with HTTP-only approaches** - requires real browser execution
- Fingerprint data includes: device hardware, Bluetooth, audio, screen, etc.
- Challenge code is dynamic and frequently updated
- Session persistence is critical - solve once, reuse cookies

**Your stack handles this:**
- Camoufox executes JavaScript natively
- Cookie transfer to HttpSession preserves solved challenge
- SmartProxy session maintains consistent IP

### Finding 5: Rate Limiting and Behavioral Patterns

**Source:** [Scrapeless - Rate Limiting](https://www.scrapeless.com/en/blog/rate-limiting)

**Detection Triggers:**
- More than 100 requests/minute from single IP
- Fixed interval between requests
- No scroll/mouse activity
- Accessing pages in sequential/predictable order
- Missing referrer headers
- Unusual request patterns (only API, no assets)

**Mitigation Strategies:**

```python
import random
import asyncio

async def human_like_delay():
    """Random delay mimicking human behavior."""
    base_delay = random.uniform(2.0, 5.0)
    # Occasionally longer pauses (reading content)
    if random.random() < 0.2:
        base_delay += random.uniform(3.0, 8.0)
    await asyncio.sleep(base_delay)

async def scroll_page(page):
    """Simulate human scrolling behavior."""
    viewport_height = await page.evaluate("window.innerHeight")
    scroll_height = await page.evaluate("document.body.scrollHeight")
    
    current_position = 0
    while current_position < scroll_height:
        # Random scroll amount
        scroll_amount = random.randint(
            int(viewport_height * 0.3),
            int(viewport_height * 0.8)
        )
        current_position += scroll_amount
        
        await page.evaluate(f"window.scrollTo(0, {current_position})")
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Occasionally scroll back up
        if random.random() < 0.1:
            current_position -= random.randint(100, 300)
            await page.evaluate(f"window.scrollTo(0, {current_position})")
            await asyncio.sleep(random.uniform(0.3, 1.0))
```

---

## Comparison Matrix

| Approach | Imperva Effectiveness | Speed | Complexity | Cost | Use Case |
|----------|----------------------|-------|------------|------|----------|
| Camoufox + Residential | High | Slow | Medium | High | Protected pages, login flows |
| Patchright + Residential | Medium | Medium | Low | High | Basic protection sites |
| curl_cffi + Residential | Low-Medium | Fast | Low | Medium | API calls after session |
| Playwright Stealth | Low | Medium | Low | Medium | Simple bot detection |
| HTTP-only (requests) | Very Low | Very Fast | Very Low | Low | Unprotected endpoints |

---

## Recommendations

### For Your Stack (Camoufox + SmartProxy)

1. **Browser Configuration:**
   ```python
   async with AsyncCamoufox(
       os=["windows", "macos"],
       headless="virtual",
       humanize=True,
       block_webrtc=True,
       geoip=True,
       proxy=proxy_config
   ) as browser:
       # Your scraping logic
   ```

2. **Session Flow:**
   - Use Camoufox for initial page load and JavaScript challenge solving
   - Transfer cookies to HttpSession (curl_cffi) for API calls
   - Maintain SmartProxy session-based IP throughout

3. **Timing Strategy:**
   - 3-7 second random delays between requests
   - Scroll pages before extracting data
   - Simulate mouse movements on interactive elements
   - Session duration: 15-45 minutes

4. **Proxy Configuration:**
   ```bash
   PROXY_TYPES=smartproxy_session
   SMARTPROXY_SESSION_LIFETIME=30  # 30 minutes
   SMARTPROXY_COUNTRY=us
   SMARTPROXY_STATE=tx  # Match expected user location
   ```

5. **Error Handling:**
   - On 403/429: Mark proxy blocked, rotate to new session
   - On CAPTCHA: Log for manual intervention or use CAPTCHA service
   - Track trust score degradation (increasing challenges = rotate everything)

### Implementation Notes

**Gotchas to Avoid:**
- Never use datacenter IPs for Imperva-protected sites
- Don't change fingerprint mid-session
- Don't skip the JavaScript challenge (reese84)
- Avoid exact timing patterns (use random jitter)
- Don't ignore scroll/mouse simulation
- Don't reuse sessions too many times

**Monitoring:**
- Log all 403/429 responses with timestamp
- Track success rate per proxy session
- Monitor for increasing CAPTCHA frequency
- Alert on sudden success rate drop

---

## Code Snippets

### Complete Camoufox Setup for Imperva

```python
from camoufox.async_api import AsyncCamoufox
from browserforge.fingerprints import Screen
import asyncio
import random

class ImpervaBypassSession:
    def __init__(self, proxy_config: dict):
        self.proxy_config = proxy_config
        self.browser = None
        self.page = None
    
    async def __aenter__(self):
        self.browser = await AsyncCamoufox(
            os=["windows", "macos"],
            screen=Screen(
                min_width=1280, max_width=1920,
                min_height=720, max_height=1080
            ),
            headless="virtual",
            humanize=True,
            block_webrtc=True,
            geoip=True,
            proxy=self.proxy_config
        ).__aenter__()
        
        self.page = await self.browser.new_page()
        return self
    
    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.__aexit__(*args)
    
    async def navigate(self, url: str):
        """Navigate with human-like behavior."""
        await self.page.goto(url)
        
        # Wait for JavaScript challenges to resolve
        await asyncio.sleep(random.uniform(2.0, 4.0))
        
        # Simulate reading the page
        await self._scroll_page()
        await self._random_delay()
    
    async def _scroll_page(self):
        """Simulate human scrolling."""
        viewport_height = await self.page.evaluate("window.innerHeight")
        scroll_height = await self.page.evaluate("document.body.scrollHeight")
        
        current = 0
        while current < scroll_height * 0.7:
            scroll = random.randint(int(viewport_height * 0.3), int(viewport_height * 0.7))
            current += scroll
            await self.page.evaluate(f"window.scrollTo(0, {current})")
            await asyncio.sleep(random.uniform(0.3, 1.5))
    
    async def _random_delay(self):
        """Human-like delay between actions."""
        delay = random.uniform(2.0, 5.0)
        if random.random() < 0.15:
            delay += random.uniform(3.0, 8.0)
        await asyncio.sleep(delay)
    
    async def get_cookies(self) -> list:
        """Get cookies for transfer to HttpSession."""
        return await self.page.context.cookies()
    
    async def get_user_agent(self) -> str:
        """Get user agent for HttpSession."""
        return await self.page.evaluate("navigator.userAgent")
```

### HttpSession with curl_cffi After Browser Auth

```python
from curl_cffi.requests import AsyncSession
from core.session import HttpSession

async def create_authenticated_http_session(
    browser_cookies: list,
    user_agent: str,
    proxy_config: dict
) -> AsyncSession:
    """Create curl_cffi session with browser cookies."""
    
    session = AsyncSession(impersonate="chrome131")
    
    # Set proxy
    session.proxies = {
        "http": f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}",
        "https": f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['server']}"
    }
    
    # Transfer cookies
    for cookie in browser_cookies:
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/")
        )
    
    # Set consistent headers
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    })
    
    return session
```

---

## Sources

1. [ScrapFly - How to Bypass Imperva Incapsula](https://scrapfly.io/blog/posts/how-to-bypass-imperva-incapsula-anti-scraping)
2. [ZenRows - Incapsula Bypass Guide](https://www.zenrows.com/blog/incapsula-bypass)
3. [ZenRows - Web Scraping with Camoufox](https://www.zenrows.com/blog/web-scraping-with-camoufox)
4. [Camoufox Official Documentation](https://camoufox.com/python/usage/)
5. [GitHub - daijro/camoufox](https://github.com/daijro/camoufox)
6. [curl_cffi Documentation](https://curl-cffi.readthedocs.io/en/v0.6.1/)
7. [GitHub - lexiforest/curl_cffi](https://github.com/lexiforest/curl_cffi)
8. [GitHub - Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)
9. [SmartProxy Best Practices](https://help.smartproxy.com/docs/best-scraping-practices-using-proxies)
10. [ScrapingAnt - Human-Like Browsing Patterns](https://scrapingant.com/blog/human-like-browsing-patterns)
11. [Rebrowser - Solving Incapsula & hCaptcha](https://rebrowser.net/blog/solving-incapsula-and-hcaptcha-complete-guide-to-imperva-security)
12. [GitHub - BottingRocks/Incapsula](https://github.com/BottingRocks/Incapsula)

---

## Open Questions

1. **CAPTCHA Solving**: When reese84 triggers hCAPTCHA, what's the best automated solving approach? (2Captcha, CapSolver, manual intervention?)

2. **Fingerprint Rotation Frequency**: How often should fingerprints be rotated to avoid behavioral pattern detection while maintaining session consistency?

3. **JA4 Fingerprinting**: As JA4 adoption grows, will curl_cffi and Camoufox need updates to their TLS impersonation?

4. **HTTP/3 Support**: Imperva is starting to analyze QUIC fingerprints - does Camoufox support HTTP/3?
