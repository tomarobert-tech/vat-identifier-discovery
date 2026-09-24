# VAT Identifier Discovery

## Overview

This project looks at whether it is possible to build a dataset of UK company VAT
numbers using only public, open sources on the web. The work has three parts.
**Part 1** covers the research: every idea I tried, how I tested it, and what
happened. **Part 2** shows a working proof-of-concept pipeline, tested on a random
sample of UK companies and checked against HMRC's public VAT tool. **Part 3** looks
at what would need to change to run this at a larger, production scale. All the code
is in this repository, and setup instructions are at the end of this document.

## Part 1 — Research

### Methodology

For every source I tried, I followed the same steps: write down a clear assumption,
test it on real UK companies from the Companies House bulk data, write down the
exact result, and only then decide if the source works or not. I tried not to guess
whether a source would work just from general reasoning — every conclusion below
comes from an actual test, not an assumption.

When a source gave zero results, I had to figure out why, because there are two very
different explanations: either the source really has no data for that company, or my
access to the source was somehow blocked. To tell these apart, I used a **positive
control**: I ran the same code on a company I already knew (from a manual check) had
a VAT number that could be found — for example, British Telecommunications or Ineo
Nuclear UK Ltd. If the control worked but the other company didn't, the source was
working correctly and simply had no data. If the control also failed, or showed
clear signs of being blocked, then the source was not reachable, and a "zero result"
did not mean anything about real coverage.

### Technical Foundations

Before testing sources for VAT discovery, I built a few things the whole project
depends on:

1. **HMRC's official "Check a UK VAT Number" API (v2.0)** needs proof that your
   organisation is registered outside the UK to get production access. This makes it
   impossible for an individual to use. Before reaching that point, I also tried
   HMRC's sandbox (test) environment, but it only recognises a small set of mock VAT
   numbers made for testing, not real ones — so it could not be used for actual
   verification either. I still applied for production access anyway, as a matter of
   due diligence, but the official channel is not really open to a solo researcher.
2. **HMRC's public VAT checker only verifies a VAT number — it cannot search for one
   by company name.** This shaped the whole project: I needed other sources to
   *find* candidate VAT numbers, and used HMRC only to *confirm* them. This
   verification step is fully automated: the script opens a session, gets a CSRF
   token, sends the form, and reads the result from the page's HTML. None of this
   was documented anywhere — I found the session/CSRF flow and the exact form field
   names (`target`, `requester`) by watching real requests in the browser's Network
   tab, not by guessing.
3. **Companies House bulk data does not contain VAT numbers.** I checked this
   myself, directly in the data columns, instead of just trusting the documentation.
4. **VAT numbers follow a checksum rule (modulus 97).** I use this as a free, local
   check before sending any candidate to HMRC — it rejects obviously wrong numbers
   without wasting a real request.
5. **A valid VAT number is not proof it belongs to the right company.** Because of
   this, every candidate goes through one more check: I compare the company name
   returned by HMRC with the company name I was originally searching for, using a
   normalised similarity score. Only a strong match counts as a real result — a valid
   VAT number attached to the wrong company is recorded as a false positive, not a
   success.

### Sources Tested

**1. Search engines (Google and DuckDuckGo)**
Assumption: searching `"<Company Name>" VAT number` would show the VAT number
directly, at least for well-known companies. I first tested this manually on
Google, on 8 random companies from the sample. Result: easy to find for large, well-known companies, but
not for smaller ones — the first sign of a pattern that repeated with every source
after this one.

I then tried to automate the same idea using DuckDuckGo's HTML search (it does not
need an API key), searching each company and scanning the top results for a VAT
pattern. On a first run of 25 companies, I got 0 candidates, and every search
request came back with an unusual HTTP status (202) instead of a normal results
page. A follow-up debug run on 5 more companies — still from the same random sample, not
well-known companies — confirmed this: 0 search results were returned for any of
them, with the identical 202 status on every single query. This uniform response,
regardless of which company was searched, is itself a sign of a block: a real "no
results" answer would normally vary by company and come back as a plain HTTP 200
(the way vat-lookup.co.uk did), not the same non-standard status every time. So I
record this attempt as blocked, not as a clean negative result.

**2. Contracts Finder** (the UK public procurement register)
Assumption: companies that supply the public sector have their VAT number listed
with the contract. Tested on 8 random companies from the sample. Result: unclear — no VAT number found
for any of them. I could not tell whether this was a limitation of the site's own
search, or whether these companies simply had no public contracts, so I record this
as inconclusive rather than a clear no.

**3. EORI number decoding**
Assumption: for a UK company registered for VAT, an EORI number has the format
`GB` + 9 digits + `000`, and those 9 digits in the middle are the same as the
company's VAT number. I confirmed this directly from HMRC's own
guidance page
(gov.uk/guidance/economic-operators-registration-and-identification-eori), which
states: *"if you are VAT registered in the UK, the first 9 digits that make up your
EORI number will be the same as your VAT number."* Tested on 8 companies from the
random sample. Result: 0/8 had a public EORI number I could find. The decoding rule
itself is correct and confirmed by an official source — the problem is that an EORI
number only exists for companies that import or export goods, and most small,
domestic companies in the sample simply never had one.

**4. VAT number published on the company's own website** (Provision of Services
Regulations 2009)
Assumption: UK businesses providing services must, by law, publish their VAT number
(if registered) on their website. Tested on the same 8 companies. Result: 0/8 — not
because the law was not followed, but because most of these companies (usually
micro-businesses) had no independent website I could find at all. The source itself
could still be valid; it simply does not apply when the company has no website in
the first place.

**5. vat-lookup.co.uk (a public aggregator, run by Datalog)**
Assumption: this site lets you search for a company's VAT number by name. In an
early test, I built a full automated pipeline (search → checksum check → HMRC
verification) and ran it on a random sample of 300 companies. Result at that time:
300/300 returned no candidate. To check this was a real result and not a bug, I ran
the same code on British Telecommunications as a positive control — it correctly
returned GB245719348. The site also answered the failing searches with a normal
HTTP 200 status and a clear message ("we may not have discovered the VAT number
yet — we typically add 20,000 new numbers per day"), not an error code. So at that
point, this was a confirmed "no data" result for small companies, not a technical
failure.

I re-ran the same search a few days later, and the result had changed: **47 out of
300 companies now returned a candidate** (a checksum-valid VAT number attached to a
row whose company name closely matched the one I searched for). This matches the
site's own claim of adding around 20,000 new numbers per day — coverage on this
source is not fixed, it grows over time. Because of this, vat-lookup.co.uk became
the actual data source behind the Part 2 proof-of-concept pipeline, described in
detail there, including the false positives it still produces even among
name-matched candidates.

**6. Endole.co.uk (a commercial company-data aggregator)**
Assumption: this commercial site publishes VAT numbers for at least some companies.
I checked this manually for 8 companies and found 1 confirmed match (Ineo Nuclear UK
Ltd — valid checksum, confirmed by HMRC, and an exact name match). When I tried to
automate this on a larger sample (40 companies), every single request came back with
an HTTP 403 error. The response showed clear signs of Cloudflare's bot protection
(`Server: cloudflare`, `Cf-Mitigated: challenge`, and a "Just a moment..." page). I
also tried `cloudscraper`, a tool made specifically to get around this kind of
protection, and still got blocked every time. So this source does have real, correct
data, but I cannot reach it automatically without more advanced tools (like a full
headless browser) or a paid data licence.

**7. Insolvency notices (The Gazette)**
Assumption: official insolvency notices might list a company's VAT number. I looked
directly at the structure of several real, published notices. Result: the standard
template only ever includes the company's Companies House number, never a VAT
number — for any company. This is a dead end based on the format itself, so there
was no need to test it on many companies individually.

**8. Common Crawl (bulk web archive)**
Assumption: instead of crawling company websites one at a time, a free archive of
already-crawled pages (Common Crawl) could be searched for VAT numbers across many
companies at once, in bulk. Common Crawl actually offers two separate tools: a
free API that only checks one URL at a time, and a paid option (AWS Athena,
roughly $1.50 per query) that can search across pages in bulk — the bulk search
the assumption needed is not free. I tested the free, single-URL tool directly, on
`vat-lookup.co.uk`, and it worked (HTTP 200, a real captured page from 12 June
2026), confirming the mechanism itself is real. Result: the free tool cannot do
bulk search, only the paid one can, so it is not meaningfully different from
crawling sites one at a time — the exact thing this approach was meant to avoid.
Verdict: not pursued further. Two reasons: the bulk option costs real money, and
this project already had a working, free source (vat-lookup.co.uk). There is also
a deeper reason it likely would not have helped anyway: small UK companies in this
project's own sample (Ramonra Ltd, Devoptimize Ltd) often had no website at all —
and a page nobody ever crawled cannot be found in any archive, bulk search or not.

**9. VIES (EU VAT Information Exchange System) — not tested**
The UK left the EU VAT system in 2021, so normal UK companies no longer appear in
VIES. The only exception is Northern Ireland businesses trading goods with the EU,
which keep an `XI`-prefixed VAT number that is still visible in VIES. This is a
narrow, specific case, so I decided it was not worth a full test for this project.

### Key Finding

What was not obvious before starting this: I expected the sources to differ mostly
in how much data they had. What actually happened is that they all failed for the
same underlying reason, just expressed differently each time — company visibility,
not company existence, is what open sources actually track.

I tested seven different sources, using a different kind of evidence each time
(clear "not found" messages, HTTP error codes, anti-bot response headers, and the
structure of official templates). The same pattern kept showing up: **VAT coverage
through open web sources depends on how visible, large, or internationally active a
company is — not on whether the company simply exists.** Large or internationally
active companies were easy to find through several sources. Small, domestic
companies were not, and for different reasons each time: no international trade for
EORI, no website for legal disclosure, no listing in aggregator databases (which are
likely built by crawling other, higher-visibility sources).

This also matches the wider picture: the UK VAT registration threshold is £90,000 of
taxable turnover in any rolling 12-month period, so a large share of small and micro
UK businesses are not VAT-registered at all. And even the ones that are registered
may simply have none of the things that would put their VAT number anywhere on the
open web in the first place — no website, no international trade, no listing with
a commercial data provider.

One more nuance is worth noting, from re-testing vat-lookup.co.uk a few days after
the first attempt (see Part 2): coverage on a given source is not fixed. It grows
over time as third-party aggregators keep crawling and indexing more of the web,
independent of how large or well-known a company is. So "coverage" is really a
moving target, not a stable property of a company.

## Part 2 — Proof of Concept

### Sample

The same random sample of 300 active UK companies used throughout Part 1, pulled
from Companies House bulk data. This is not a hand-picked or well-known set — it is
meant to represent the real population of UK companies, which is mostly small
businesses.

Building this sample was not completely straightforward. The full Companies House
bulk file is too large to load into memory at once — an early attempt crashed with
a memory error, fixed by reading it in a sample instead of loading the whole file.
An even earlier attempt accidentally used only the first 100 rows of the file as
the "sample," which is not random at all, and deleted the original source file in
the process — a real risk of losing the underlying data. Both problems were caught
and fixed before they reached the final 300-company sample, but they are worth
mentioning: building a genuinely random sample from a large file is its own small
technical problem, not something to take for granted.

### Pipeline

The pipeline runs in two separate phases, because they behave very differently:
discovery is fast and has no real limits, while verification is slow and
constrained by HMRC's own rate limit (see Results). Splitting them also means a
slowdown in one phase never blocks the other.

**Phase A — Discovery** (run once, on all 300 companies)
1. Search vat-lookup.co.uk by company name.
2. Parse the results table from the response page, capturing the company name and
   VAT number listed in each row.
3. Reject any number that fails the local checksum check (modulus 97) before it
   counts as a candidate — this is free and instant, no request needed.
4. Out of the remaining valid-checksum rows, keep the one whose company name is the
   closest match to the company being searched (using the same normalised
   similarity score as in Part 1).

**Phase B — Verification** (run only on the candidates Phase A found)
5. Send the candidate VAT number to HMRC's public checker, with a deliberate delay
   between requests (seconds at first, later increased to tens of seconds — see
   Results) to avoid triggering rate limiting in the first place, not just to
   recover from it after the fact.
6. Read the result from the final URL of the response (`/known` for a valid VAT,
   `/unknown` for an invalid one).
7. If HMRC responds with "Too Many Requests" (HTTP 429), wait and retry a limited
   number of times; if it still fails, mark the candidate as unresolved rather than
   guessing an outcome.
8. For any candidate HMRC confirms as valid, compare the registered name HMRC
   returns with the original company name, and only count it as a real match above
   a similarity threshold.

### What I fixed along the way

The pipeline above is the final version. Getting there took four rounds of
debugging, each one caught by comparing results across repeated runs rather than
trusting a single run:

- **A regex that missed real VAT numbers.** An early version looked for a VAT
  number using a "word boundary" pattern (`\b(\d{9})\b`), expecting a clear break
  between "GB" and the digits right after it. This does not work: a letter and a
  digit count as the same kind of character to a word-boundary check, so "GB"
  followed directly by 9 digits, with no space between them, never matched at
  all — missing real candidates that were sitting right there in the page.
  Matching "GB" directly, followed by an optional space and then the digits, fixed
  it.
- **Non-deterministic candidates.** An earlier version of step 2 skipped the table
  structure and just scanned the whole page for anything shaped like a VAT number.
  Some searches returned more than one row — for "Tesco," a single results page had
  24 different candidate VAT numbers on it — so which one got picked was not
  reliable, and the same 300 companies gave different results on different runs.
  Parsing the table properly (step 2) and picking by name similarity (step 4) fixed
  this.
- **A text-matching bug in step 6.** An earlier version checked the page text for
  the word "valid" instead of the response URL. This is broken, because "**in**valid"
  also contains "valid" as a substring — so rejected VAT numbers were briefly read
  as accepted. Switching to the URL fixed it.
- **A missing final check.** Before step 8 existed, any VAT number HMRC confirmed as
  valid was immediately counted as a match. This missed a real case (see Results,
  Umberslade) where a valid, active VAT number belonged to a different, related
  legal entity, not the company being searched for.
- **A resume bug in the retry script.** `slow_verify.py` (used to verify the
  discovered candidates one at a time, with long delays — see Setup) skipped any
  company already present in its results file, regardless of status, including
  ones still marked `RATE_LIMITED`. This meant re-running it on the last 3
  unresolved candidates did nothing at all, since they were technically "already in
  the file," just with an unresolved status — it looked like HMRC was still
  blocking them, when actually the script was not attempting them any more. Fixed
  by excluding `RATE_LIMITED` entries from the "already done" check, so they get
  retried instead of skipped forever.

### Results

Running the search step (steps 1–2) on all 300 companies found **47 candidates
(15.7%)** — a checksum-valid VAT number attached to a table row whose company name
closely matched the target. This is a real, growing number: an earlier version of
this same search, run a few days earlier, found 0 candidates out of the same 300
companies. vat-lookup.co.uk's own message ("we typically add 20,000 new numbers per
day") appears to be accurate.

Verifying all 47 candidates against HMRC (step 3) turned out to be limited by
HMRC's own service, not by anything in this project's code. Across three full runs
of the pipeline on the same 300 companies on the first day (close to 900 companies
processed in total, plus extra manual tests), and a few hundred more the next day,
the public VAT checker started returning HTTP 429 ("Too Many Requests"), and this
did not clear up after short pauses (minutes) or even after several hours — it
behaved like a sustained, per-IP quota rather than a short burst limit. Spacing
requests out patiently, across two separate sessions on two different days,
eventually got all **47 candidates fully verified**. The last 3 needed a manual,
single-request check the next day (by then, HMRC's rate limit had cleared) — the
retry script itself turned out to have a bug that was silently skipping them
instead of retrying them, found and fixed only after the manual check already had
the real answer (see "What I fixed along the way"). Full, row-by-row results are
saved in `final_verified_results.json`; the table below shows a representative
selection.

| Company | vat-lookup.co.uk candidate | HMRC result |
|---|---|---|
| RAMONRA LTD | GB314660128 | Valid, exact name match — **confirmed** |
| WPS LIVERPOOL LTD | GB381634978 | Valid, exact name match — **confirmed** |
| SWIFTSURE DESIGN LIMITED | GB144026249 | Not a registered VAT number at all — **false positive (bad source data)** |
| UMBERSLADE CORPORATE MANAGEMENT LIMITED | GB559123631 | Valid, but registered to "Umberslade Corporate Management Limited **Directors Pension Fund**" — a related but different legal entity — **false positive (wrong entity)** |
| TUODA TRADING LTD | GB401121477 | Valid, but registered to "Shenzhenshi Feng Tuoda Trading Company Ltd" — an unrelated company with a similar name — **false positive (wrong entity)** |
| METIER LIMITED | GB241426533 | Valid, but registered to "Metier London Limited" — a different company with a similar name — **false positive (wrong entity)** |

### False Positive Rate & Limitations

Out of all 47 fully verified candidates, **33 were genuine matches and 14 were
false positives — a false positive rate of 14/47 ≈ 30%**. This is a solid number,
on the full discovered set, not a small subsample, and it splits cleanly into two
different causes:

1. **Bad source data (11 of the 14 false positives).** vat-lookup.co.uk listed a
   VAT number that HMRC says is not a valid, registered number at all — the same
   pattern as Swiftsure Design Limited. This is a data quality problem with the
   third-party source, not a matching problem.
2. **Wrong entity, right name pattern (3 of the 14 false positives).** In these
   cases, the VAT number is real, active, and correctly confirmed by HMRC — but it
   belongs to a different legal entity than the company being searched for. Besides
   Umberslade (the company's own pension fund), this also happened for Tuoda
   Trading Ltd (matched to an unrelated company that happens to share "Tuoda
   Trading" in its name) and Metier Limited (matched to "Metier London Limited," a
   different company with a similar name). This is the exact risk described in the
   original brief: a plausible-looking, valid VAT number attached to the wrong
   company. All three were only caught because of the final name-check step
   described above; without it, all three would have been recorded as correct
   matches.

The split matters: about four fifths of the false positives here are loud and
easy to catch (HMRC flatly rejects the number), but about a fifth are quiet — a
fully valid, HMRC-confirmed VAT number that still points at the wrong company. That
quieter kind is the one the brief specifically calls dangerous, because nothing
about the candidate itself looks wrong on the surface.

One reassuring data point on the matching logic: for Elvaston Engineering
Consulting Limited, HMRC's own records contain a small typo in the registered name
("Consult Ing Limited," with an extra space). The 0.85 similarity threshold was
loose enough to still accept this as a match, without being loose enough to accept
any of the 14 false positives above — a reasonable balance on this sample, though
not something to assume holds perfectly at a much larger scale.

**HMRC's own verification service was also a real bottleneck**, separate from
candidate discovery. 3 of the 47 candidates needed a third verification attempt,
on a separate day, before HMRC stopped rate-limiting them — the free checker
clearly was not built for this kind of repeated automated use. Any future work on
this project should treat verification throughput, not just candidate discovery,
as a real constraint to plan around.

One more open question, not resolved within this project: a search for "BP" on
vat-lookup.co.uk returned nothing, while British Telecommunications, British
Airways, Vodafone, and Tesco — tested the same way — all returned a candidate. A
plausible guess is that very short or generic company names are handled
differently by their search, but this was not tested further.

## Part 3 — Scaling to Production

### Cost Considerations

The real cost of this project is not developer time — it is the cost of dealing
with the protections that sources put up once you go past a small, manual scale.

- **Endole.co.uk** has real VAT data, but it is protected by Cloudflare, and this
  held up against both a plain `requests` client and `cloudscraper`, a tool made
  specifically to get past this kind of protection. Reaching it reliably would
  likely need a full headless browser (a tool like Playwright, which opens and runs
  a real browser in the background, just without a visible window). This is much
  slower than the plain HTTP requests this project uses everywhere else: a real
  browser has to load the whole page, run all of its JavaScript, and wait for the
  Cloudflare check to finish, which can take several seconds per company instead of
  well under one second. And even then, it is not guaranteed to work, since bot
  protection keeps changing.
- **HMRC's free public checker** — the one this whole project relies on for
  verification — has a real, strict rate limit. This project hit it directly: after
  three full runs of the pipeline on the same 300 companies on the first day (close
  to 900 companies processed in total, plus extra manual tests), and a few hundred
  more the next day, the checker returned "Too Many Requests" for more than a day,
  even with long pauses in between. HMRC's official production API would likely
  handle more volume, but it requires proof of organisational registration outside
  the UK, which rules out an individual or a small team without that setup.
- If a source like Endole turns out to have good coverage, the realistic way to use
  it at scale is not more scraping engineering — it is a paid data licence, a
  recurring commercial cost rather than a one-time technical one.

### Rough Cost Per Company

Splitting this into three separate pieces, since each behaves differently:

**Discovery** (reaching a protected aggregator like Endole, once past Cloudflare):
commercial anti-bot bypass services charge roughly $1.30–$3.00 per 1,000 requests
for medium-to-high Cloudflare protection (published pricing from ScrapeOps, a
real anti-bot bypass provider) — about **$0.001–$0.003 per company**. This assumes
the aggregator's own data is worth reaching in the first place; it says nothing
about accuracy.

**Verification** at the scale of the UK's ~2.18 million VAT-registered businesses
(the figure given in the brief):

| | Free (HMRC direct) | Paid (Vatstack, a VAT-validation API with published pricing) |
|---|---|---|
| Cost for ~2.18M validations | £0 | ~$21,800 ($150 base + 2,165,000 × $0.01 per additional) |
| Time to complete | Cannot be estimated with confidence — this project measured a block lasting over a day after well under 1,000 automated checks, with no predictable reset | Much faster — a commercial service built for production volume, with published rate limits |
| Code complexity | High — session handling, CSRF tokens, retry, backoff, checkpointing (all built for this project) | Low — a stable, documented API, no need to reverse-engineer a session flow |
| Infrastructure cost | Minimal (a few pounds of compute time) | Included in the service price |

The free path costs nothing in money, but its real cost is unpredictable delay,
not currency — exactly what this project ran into directly.

**Human audit** (catching cases like Umberslade, Tuoda Trading, and Metier, where a
valid VAT number belongs to the wrong company): assuming a random 10% of confirmed
matches get checked by hand, at around 2 minutes each, and roughly £15–20/hour for
a junior analyst: `0.10 × (2/60 hour) × £15–20 = £0.05–£0.07 per company`, averaged
across the whole dataset. These numbers (10%, 2 minutes, £15–20/hour) are stated
assumptions, not sourced figures — but the shape of the calculation is what
matters: a small, fixed share of manual review, spread across every company
processed.

Put together, the pattern worth arguing about is this: **the human audit step, not
the scraping infrastructure, looks like the largest cost per company** — the
opposite of the usual assumption that scraping is the expensive part.

**Adding all three together**, converting to one currency (1 USD ≈ £0.75 at time
of writing): discovery (~£0.001–£0.002) + verification via a paid service like
Vatstack (~£0.0075) + human audit (~£0.05–£0.07) comes to **roughly £0.06–£0.08 per
company**. Using the free HMRC checker instead of Vatstack barely changes this
total, because the audit step dominates either way — the real difference between
the free and paid path is not the money, it is the unpredictable delay of the free
option, which this figure does not capture at all.

### What Breaks First

Based on what actually happened in this project, the answer is clear: **rate limits
and bot protection break first, on both ends of the pipeline, well before compute
or storage become a concern.**

- On the discovery side, a commercial aggregator (Endole) blocks automated access
  outright, and even a plain search engine (DuckDuckGo) started rate-limiting after
  around 25 automated queries.
- On the verification side, the free HMRC checker — the only verification method
  available without a business registration — turned out to have a strict, lasting
  per-IP limit, confirmed directly rather than assumed.

This means the real throughput ceiling for a production version of this project is
not "how many companies can be searched," but **"how many verifications can
actually be completed per day,"** which is a much smaller number and needs to be
planned around from the start, not discovered by accident like it was here.

### Monitoring

A production version of this system would need to watch for the same problems this
project ran into, on an ongoing basis:

- **Coverage over time.** Coverage is not fixed — vat-lookup.co.uk went from 0
  candidates to 47 candidates on the same 300 companies over about two days. A
  production system should re-run discovery periodically instead of treating "not
  found" as a permanent answer.
- **False positive rate, checked by hand.** Even with a checksum filter, an HMRC
  confirmation, and a name-similarity check, this project still found three valid,
  active VAT numbers that belonged to the wrong legal entity — the Umberslade,
  Tuoda Trading, and Metier cases from Part 2. A production system should
  regularly sample confirmed matches and check them by hand, especially for
  close-but-not-exact name matches.
- **Source health.** Sources can tighten their protection at any time — this is
  likely what happened with Endole, and it is not documented anywhere in advance. A
  production system should track failure and block rates per source over time, and
  flag it when a source that used to work suddenly starts failing consistently,
  since that usually means a policy or protection change, not a temporary issue.
- **Verification throughput.** Specifically for HMRC, tracking the rate of "Too Many
  Requests" responses would show early when the free checker is no longer enough,
  and when it is time to invest in the production API path instead.

## Debate Topics

### Brute-forcing the checksum

A 9-digit VAT number has 1 billion possible combinations, but the checksum rule
narrows valid ones down to roughly 1 in 97 of them — still around 10 million valid
numbers. In theory, checking all 10 million against HMRC's public checker would
turn a "verify only" tool into a full discovery tool: every valid number returns a
registered name and address, so this would, in effect, reconstruct HMRC's entire
VAT registry from the outside.

It is not a good idea, and this project has direct evidence why. HMRC's free
checker started returning "Too Many Requests" after well under a thousand
automated checks, and the block lasted for more than a day. Brute-forcing 10 million numbers is a completely different scale from that. It
would also likely break HMRC's terms of use. HMRC already offers two separate
ways to use their service: a free checker for occasional, individual lookups, and
a gated production API for real volume, which requires proof of business
registration (this project applied and was refused — see Technical Foundations —
though whether the production API itself has a cost was never confirmed).
Brute-forcing the free checker to get the same result as the
production API — the entire registry — means using the wrong tool to get around
the rule, not just a technical shortcut.

### Keeping the dataset current

Companies register and deregister all the time, so a one-time discovery pass goes
stale. Re-running full discovery on all 4.2 million UK companies on a regular
schedule would be wasteful and would run straight into the same rate limits found
in this project. A more realistic approach:

- Track new company registrations. The bulk file this project used is only
  updated monthly, but Companies House also runs a separate Streaming API for
  real-time change notifications (new companies, filings, insolvencies) — a
  different product from the one used here, not tested in this project, but the
  right one to look at for this. Only run discovery on companies that are
  actually new.
- Track dissolutions and retire those VAT records instead of continuing to check
  them.
- Re-check companies with a "not found" result on some regular cadence, rather than
  treating it as permanent — this project directly measured coverage on the same
  source going from 0/300 to 47/300 in about two days, so "not found today" clearly
  does not mean "not found ever."
- Re-verify confirmed matches against HMRC occasionally, since a company can
  deregister for VAT (or stop trading) without being dissolved as a company.

### Knowing the dataset is wrong, with nothing complete to check against

Without a full reference dataset, correctness has to be checked indirectly:

- **Cross-source agreement.** If two independent sources point to the same VAT
  number for the same company, that is stronger evidence than either source alone.
  When sources disagree, that is a clear signal to review by hand.
- **Manual audits on a random sample of confirmed matches** — not just failures.
  This project found three such cases (Umberslade, Tuoda Trading, Metier), each
  with a valid, HMRC-confirmed VAT number, and each would have passed as a normal
  success without a human noticing the mismatch in legal entity.
- **Tracking the false positive rate found through these audits over time**, and
  tightening the name-matching threshold if it drifts upward.
- **Downstream signals.** Since the real use case is matching invoices to
  suppliers, a wrong VAT number would eventually show up as a reconciliation error
  on the customer's side. That feedback loop is slow, but it is a real, independent
  check that this project's own testing cannot provide by itself.

### Sources I would not use in a commercial product

**Endole.co.uk.** It is a commercial company-data product, and it actively blocks
automated access with Cloudflare, which is a clear signal about how they want their
data used. Even if it were technically reachable, scraping and reselling a
competitor's aggregated data without a licence is not something I would put behind
a paid product — if the data is genuinely valuable, the right path is a licensing
conversation with them, not quiet scraping.

I would also be careful about **any single third-party aggregator used as a sole
source**, including vat-lookup.co.uk, which worked well for this project but also
returned 11 VAT numbers (out of the 14 total false positives — see Part 2) that
HMRC says are not valid at all, Swiftsure Design Limited among them. Aggregators
do not usually say where their numbers come from, so there is no
way to audit their reliability directly — unlike HMRC, which is the authoritative
source. And **HMRC's free public checker itself** was never meant to be a
production backend — using it as if it were, at real commercial volume, runs into
the same rate limit this project hit directly, rather than going through the
gated, licensed production API instead.

## Beyond the UK: Germany

Germany is the obvious next market for this customer, but the problem does not
just scale up the same way — it flips in an interesting way.

### Three identifiers, not one

The UK has a single VAT number per company. Germany has three separate tax
identifiers, issued by different authorities, for different purposes: a domestic
tax number (Steuernummer) used on invoices to German clients, a personal tax ID for
individuals (not relevant here), and a VAT ID for EU cross-border trade
(Umsatzsteuer-Identifikationsnummer, or USt-IdNr) — DE followed by 9 digits. A
company only needs a USt-IdNr if it actually trades across EU borders, similar to
how only some UK companies had an EORI number in this project.

### Discovery may be easier

German law requires most commercial websites to publish a legal notice page
(Impressum), which commonly includes the Steuernummer. This looks like a much more
consistently followed rule than the UK's website VAT disclosure requirement, which
this project found barely applied in practice — mostly because small UK companies
often had no website at all.

A quick, informal check on small, local German businesses (not a rigorous sample
like the 8-company tests in Part 1 — just a spot check, and one initial result
turned out not to even be a German business, so it was dropped) found a
Steuernummer listed for 2 out of 3 genuine examples, and a USt-IdNr for none of
them. The one with nothing findable was a registered sports club (e.V.) rather
than an ordinary company — German non-profit associations are often not
VAT-registered at all, so this may not be a fair comparison, and it is left as an
open question rather than a confirmed finding. Still, the pattern points the same
way as the EORI finding in the UK: an internationally-relevant identifier
(USt-IdNr) was absent from purely local businesses, while Impressum coverage,
though it looks more consistent than the UK's website VAT disclosure, is not
confirmed to be universal either.

### Verification is harder, in a different way

This is where it flips. Only the USt-IdNr (the EU cross-border VAT ID) can be
checked against a public system — the EU's VIES, the same VIES this project ruled
out for the UK after Brexit. The Steuernummer — the one actually shown on invoices
and websites — has no public database where a third party can confirm it is real
or active. So the easier-to-find identifier is the harder-to-verify one, and the
easier-to-verify identifier (via VIES) only exists for companies trading
internationally, which is likely a minority of small domestic businesses — the same
shape of problem as the EORI dead end found in the UK.

One more wrinkle, worth flagging even though it comes from a third-party source
rather than an official one: several VIES integration guides note that VIES does
not return a registered business name for German numbers at all, even when the
number checks out as valid. If that holds up, it means the name-comparison
safeguard this project relies on everywhere else — the one that caught Umberslade,
Tuoda Trading, and Metier — would not be usable for Germany even in the cases
where verification does work.

### Would the pipeline survive the move?

Not directly. The checksum algorithm is different (Germany's USt-IdNr uses ISO 7064
Mod 11,10, not the UK's modulus 97), and the overall shape of the problem is not
the same — this is not "the same pipeline, more requests," it is "easy and hard
have swapped sides." The one piece that would genuinely carry over is the
name-comparison and false-positive check built in `verify_helper.py`: a plausible
number attached to the wrong company is exactly as real a risk in Germany as in the
UK, and that part of the logic is not UK-specific.

One more thing worth watching: Germany started rolling out a new permanent business
identifier (Wirtschafts-Identifikationsnummer, W-IdNr) in November 2024, assigned
automatically rather than applied for, meant to become a stable identifier on
invoices from the end of 2026 onward. If a public registry for it appears later,
it could eventually close the exact verification gap described above — worth
checking again before building anything long-term around Steuernummer discovery.

### A country where VAT is barely discovered at all

For five EU countries — Latvia, Cyprus, Ireland, Malta, and Slovakia — a company's
VAT number cannot be worked out from its registration number, and is not
available through any registry API (confirmed directly from a VAT-validation
provider's technical documentation). The only way to check one is a reverse
lookup through VIES: you enter a VAT number and get a company name back, never
the other way round. Malta is a clean single example: there is no path from "I
have this company's name" to "here is its VAT number" — not through VIES, not
through a registry, not through anything public. You can only confirm a number
you already have.

This is a harder version of the UK's own problem. In the UK, at least a few
sources (however small their coverage) let you search by name. For Malta and this
group of five, name-based discovery does not appear to exist as a path at all —
only verification does.

What this implies for prioritising markets: coverage should not be assumed to
scale smoothly from country to country, and "the identifier exists and is
checkable" (true for all five of these, via VIES) is a different fact from "the
identifier can be found by starting from a company name" (false for all five).
Both have to be checked per country, not assumed together.

### Which countries are genuinely hard, and where

Putting the UK, Germany, and Malta-type findings together suggests three
different shapes of "hard," not one:

- **Hard discovery, easier verification (UK).** No way to search by name, but a
  free public checker once you have a candidate.
- **Easier discovery, hard verification (Germany).** The identifier that is
  actually shown on websites (Steuernummer) cannot be checked anywhere; the one
  that can be checked (USt-IdNr) only exists for cross-border traders, and does
  not even return a name to compare against.
- **No discovery path at all, verification-only (Malta, Cyprus, Ireland, Latvia,
  Slovakia).** VIES can confirm a number you already have, but there is no route
  from a company name to a candidate number in the first place.

The practical conclusion: "the UK was hard" does not generalise into a single
difficulty score for other countries. Each one needs its own version of Part 1 —
the same assumption-test-result process — before assuming it is easier, harder, or
the same shape of problem.

## Setup / How to Run

```bash
pip install -r requirements.txt
```

**Main pipeline**, in the order they're meant to run:

1. `generate_sample.py` — builds the random 300-company sample from a Companies
   House bulk data ZIP file (download separately from Companies House — the file is
   too large to include in this repository), saves it to `sample_companies.json`.
2. `discovery.py` — runs the candidate search step (vat-lookup.co.uk) on all
   300 companies, with no HMRC calls at all. Saves to `discovery_only_results.json`.
3. `slow_verify.py` — verifies the discovered candidates against HMRC, one at a
   time, with a long delay between each request. Saves to
   `final_verified_results.json`, the final result used in Part 2. This step is the
   one limited by HMRC's rate limit (see Part 2 and Part 3); it can be safely
   stopped and re-run, and picks up where it left off.

`pipeline_results_fixed.json` is kept from an earlier, interrupted full-pipeline
run — it is evidence of the rate-limiting problem described in Part 2 and Part 3,
not the final result (that is `final_verified_results.json`).

`pipeline.py`, `pipeline_fixed.py`, and `verify_helper.py` are shared modules
(checksum check, structured candidate extraction, HMRC verification, name-similarity
matching) imported by the scripts above — they are not meant to be run directly.

**Supporting and exploratory scripts**, kept for transparency (referenced directly
in Part 1 and Part 2 as evidence for specific sources or bugs, not part of the
final pipeline): `main.py`, `test_isolation.py`, `test_hmrc.py`,
`test_duckduckgo.py`, `test_search_5.py`, `ddg_pipeline.py`,
`debug_ddg_pipeline.py`, `debug_vat_lookup.py`, `test_endole_source.py`,
`test_endole_cloudscraper.py`, `test_new_sources.py`, `debug_hmrc_reject.py`,
`test_common_crawl.py`.

The `debug_response_1_*.html` and `debug_response_2_*.html` files are raw evidence
from `debug_vat_lookup.py`, saved during the vat-lookup.co.uk testing described in
Part 1 (British Telecommunications as the positive control, and Edelweiss Cheddar
Limited showing the "not discovered yet" message). `endole_results.json` is the
saved output from the automated Endole test in `test_endole_source.py` that hit
Cloudflare's block. None of these are needed to run anything — kept for
transparency.