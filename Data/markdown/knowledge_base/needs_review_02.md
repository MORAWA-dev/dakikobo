---
title: "Prepared for: Agricultural development practitioners, digital innovation teams, extension"
source_file: knowledge_base/needs_review_02.pdf
doc_type: unknown
language: en
country: Burkina Faso
crops: [sorghum, millet, maize, cotton, cowpea, groundnut]
topics: [fertilization, sowing, pest_disease, climate, soil, yield]
page_count: 12
chars: 31384
extracted_with: pdfplumber
converted: 2026-06-26
---

# Prepared for: Agricultural development practitioners, digital innovation teams, extension

Prepared for: Agricultural development practitioners, digital innovation teams, extension
officers, and agripreneurs designing technology for smallholder farmers in West Africa and
Burkina Faso.
Report Date: November 2025
Geographic Focus: West Africa (emphasis on Burkina Faso)
Time Period Reviewed: 2020–2025
Digital agriculture tools and AI-powered advisory services hold genuine promise for African
farmers facing climate shocks, market barriers, and resource constraints. Yet between the
marketing claims and on-farm reality lies a substantial gap. Farmers in West Africa and
Burkina Faso report that tools marketed as "intelligent," "adaptive," and "locally tailored"
frequently deliver generic advice, fail in low-connectivity settings, operate in foreign
languages, and often do not account for the actual crops, soils, and seasonal dynamics
farmers know.
This report documents five critical gaps between aspiration and implementation, grounded
in recent discussions (2020–2025) with farmers, extension workers, agripreneurs, and
development practitioners, as well as analysis of institutional reports from FAO, World
Bank, CGIAR, IFAD, and digital agriculture case studies. The report then outlines actionable
recommendations for tool developers, extension services, and farmers on how to choose,
adapt, and scale digital agriculture effectively.[1][2][3][4][5]
Farmers cite unreliable or poorly localized weather information as their top digital
agriculture frustration.[2][4] Global weather models and continental-scale forecasting
systems often miss the hyperlocal rainfall patterns, micro-climates, and seasonal quirks
that determine whether a planting date will succeed or fail in a specific district or even a
specific village.[6][7] Seasonal forecasts for the West African Sahel show persistent
Digital Agriculture Gap Report: West Africa
and Burkina Faso
Bridging the Distance Between Tool Design and Farmer
Reality
Executive Summary
## 1. The Five Critical Gaps
Gap 1: Weather Information Is Unreliable or Inaccessible
underperformance, with models exhibiting dry bias and poor calibration at critical midrange quantiles (rainfall amounts between 20–90 percent of normal).[7]
In addition, more than half of Africa's radar stations lack the capacity to produce accurate
enough data for medium-range weather predictions.[8] Tools that claim to "predict the next
10 days of rainfall" often perform no better than a local elder's historical observation,
especially during irregular or extreme seasons—exactly when farmers need the most
guidance.[8]
Farmers in rain-fed agricultural systems make planting decisions around three weeks
before the onset of rains. If the weather forecast is wrong by a week or more, or if it misses
localized thunderstorms or dry spells, farmers commit resources (labor, seed, fertilizer) to a
crop that may fail. In Burkina Faso and the Sahel, where soils are fragile and input costs are
high relative to income, this risk deters adoption of any new technology—digital or
otherwise.[9]
Some platforms (e.g., M-Shamba in Kenya, platforms in Senegal) deliver weather
alerts via SMS or IVR (Interactive Voice Response), which works on feature phones.
However, the accuracy of the underlying forecast remains modest.[10]
National meteorology agencies (e.g., ANAM in Burkina Faso) provide agrometeorological bulletins intended to guide farming decisions, yet their dissemination
is limited and often in French or French-dominant formats, missing farmers in
outlying areas who speak Moore, Dioula, Fulfuldé, or other local languages.[3]
Farmers in Burkina Faso report that radio programs mentioning agriculture often
reflect limited agricultural extension knowledge, and WhatsApp weather links rely
on internet that half the rural population lacks.[3]
1. Collaboration with national meteorology agencies and local agricultural research to
validate forecasts at district and sub-district scales, not just national averages.
2. Integration with user feedback loops: if a forecast is wrong, the system learns why
and adjusts parameterization for next time.
3. Transparent communication of forecast uncertainty ("60% confidence rain will fall
between 15–50 mm on day 7") rather than point predictions.
4. Dissemination in local languages via SMS, IVR, and voice calls, not just web or app
interfaces.
Advisory platforms marketed as "AI-driven" and "personalized" frequently provide blanket
recommendations (e.g., "apply 100 kg/ha of NPK fertilizer") that do not account for local
crop varieties, soil types, prior yields, or farmer-specific constraints.[1][4][11] West African
farmers cultivate dozens of crops and hundreds of local varieties: sorghum, millet, maize,
cowpea, groundnut, cassava, rice, shea, cotton, and many others. Each has distinct
Gap 2: Crop-Specific and Soil-Specific Advice Is Generic or Absent
phenology, water demand, pest profile, and soil nutrient requirement. Few digital tools can
model more than two to three crops with any agronomic depth.[1]
Moreover, soil heterogeneity within a single farm or village is extreme. Farmers know this:
they speak of "black soil," "sandy soil," "stony soil," with intuitive understanding of which
crops suit which patches. Digital tools rarely incorporate this hyper-local soil knowledge.
Instead, they rely on coarse global soil maps or ask farmers to purchase soil testing—a
service many cannot afford, and even fewer trust.[3][4][11]
When a tool recommends a crop or practice that does not match a farmer's soils or
varieties, the farmer loses trust in all digital advice. This is not abstract risk aversion; it is
rational skepticism. A farmer who loses money following a generic recommendation will
not retry digital advisory, and word spreads quickly in communities.[11]
Additionally, Sahel soils are often low in organic matter, prone to crusting, and highly
sensitive to input timing. A recommendation that works in Kenya (higher rainfall, deeper
soils) will fail in Burkina Faso. Yet many platforms are built on datasets from East or
Southern Africa and scaled without regional recalibration.[1][4]
A 2023 Burkina Faso case study found that the Ministry of Agriculture and Animal
Resources (MARAH) has developed agro-meteorological advisory services via
Viamo's IVR system (short number 321) that provide information in local languages,
but the content is seasonal and general (e.g., "This is the planting season for
sorghum"), not tailored to individual farmer plots or varieties.[3]
Platforms like Complete Farmer (Ghana) and M-Shamba (Kenya) integrate expert
agronomic input via call centers, but scale is limited to a few crops and regions.[1][4]
Soil-mapping initiatives (e.g., Zenvus in Nigeria, catering to precision agriculture)
exist, but cost is prohibitive for smallholders. These are typically used by larger-scale
or contract farming operations.[1]
1. Farmer-validated crop and variety profiles built from on-farm trial data in each
agroecological zone (Sahel, Sudan savanna, guinea savanna, for Burkina Faso).
2. Soil testing kits that are affordable and integrated with advisory (e.g., farmer takes a
simple soil color and texture photo; AI + local extension interpret it).
## 3. Agronomy rules that encode the decision logic of respected local farmers and
research agronomists, with transparency: "For this soil type and rainfall pattern,
sorghum variety X yields Y% better than variety Z."
4. Multi-year feedback: if advice fails, the system documents why and updates the
model.
5. Modular design so that advice for a specific crop (e.g., cowpea in sandy soil) can be
added and validated independently without rebuilding the entire platform.
AI-powered disease diagnosis apps (e.g., PlantVillage, Plantix) use image recognition to
identify crop diseases and pests. In principle, this is transformative: a farmer photographs
a sick leaf, the app diagnoses the problem and recommends treatment. In practice, several
challenges persist.[12][13]
First, most image-recognition models are trained primarily on images of diseases in
temperate crops or large-scale cash crops (maize, wheat, rice, tomato). Local Sahel crops—
millet, sorghum, cowpea, bambara groundnut, fonio, shea, baobab—are vastly
underrepresented or absent from training datasets.[12][13] A farmer with sick millet plants
will get a "no diagnosis found" or a misidentification, destroying trust.[13]
Second, the app diagnoses the disease but does not account for context. In a farmer's field,
a disease may be present because of prior flooding, soil compaction, or lack of rotation—
issues the photo alone cannot reveal. The app recommends fungicide; the farmer sprays,
but the disease recurs because the root cause (waterlogging) was never addressed.[4][12]
Third, even where diagnosis is accurate, recommended treatments (chemical names,
dosages) may not be available locally, or the farmer may lack the cash to buy them at the
moment treatment is needed.[1][4][11]
Pests and diseases are among the top five reasons farmers lose crops in West Africa. Rapid,
accurate diagnosis could save yield; wrong or incomplete advice squanders the farmer's
response window. The result: farmers revert to intuition, neighbor advice, or (more
commonly) accept the loss, then become reluctant to try any new advisory tool.[1][4][12]
[13]
PlantVillage Nuru (CGIAR) and other initiatives have built databases of disease and
pest images for major African crops, but these remain geographically and cropspecific biased.[12]
Some NGOs and extension services combine photo-based apps with human expert
verification via WhatsApp or a call center (e.g., CABI's Plantwise Knowledge Bank),
which raises accuracy but reduces scalability and introduces human bias.[1][4]
FarmView (Carnegie Mellon, deployed in Mozambique) includes speech-to-text so
farmers can describe the problem if photos are unclear, but such services are rare
and not scaled to Burkina Faso.[1]
1. Crowdsourced imagery: farmers photograph their own diseased crops with the app;
human experts (extension agents, researchers, experienced farmers) verify the
diagnosis and suggested treatment; the app learns from each case.
2. Treatment recommendations tied to local availability and affordability: "For this
disease, recommended treatments are: (a) sulfur dust (widely available, affordable);
Gap 3: Pest and Disease Diagnosis Is Unreliable, Lacking Local Crops, or
Insufficient Without Expert Follow-Up
(b) insecticidal soap (harder to find locally); (c) neem-based spray (common practice
locally)."
3. Agronomic context integration: if a photo shows a disease that typically occurs after
flooding, the app asks "Has this field been waterlogged recently?" and suggests
drainage or intercropping as preventive measures.
4. Sahel-crop datasets: active collaboration with ICRISAT, national research programs,
and farmer groups to photograph and label millet, sorghum, cowpea, groundnut, and
other crops at all growth stages and disease states.
5. Connection to input supply: the app integrates with local agrodealer networks so
treatment recommendations link to actual products available within 5 km, at known
prices.
Smartphones in Burkina Faso are concentrated among urban youth and the middle class.
Most rural farmers rely on basic feature phones (2G/3G, no app store, limited processing
power) or older Android smartphones with < 2 GB RAM. Yet many digital agriculture tools
require smartphones with high specifications, stable 4G or 3G connectivity, and frequent
internet access to function.[3][4][11]
Additionally, rural connectivity is intermittent. A farmer in a northern region may have
signal in the morning but none by afternoon, or signal only on hilltops. Tools that require
constant connection fail when farmers are in fields during the most critical decision
moments (early morning, during storms, at field edges).[3][4][11]
Many platforms lack offline-first architecture. This means they cache nothing locally; they
constantly fetch from the cloud. In low-bandwidth zones, users see spinning loading icons,
timeouts, and frustration. If the user pays per megabyte for data (as is common in rural
Africa), the cost becomes prohibitive.[4][11]
If a tool does not work on the phone a farmer actually owns, or it costs too much data to
use, adoption will remain near zero regardless of the quality of the advice. Aspirational
design ("farmers will upgrade to smartphones") ignores the economic reality: a basic
feature phone costs $5–15 used; a modern smartphone costs $100+, representing a month's
income.[3][4][11]
Additionally, women, youth, and IDPs (internally displaced persons) in conflict-affected
regions often lack reliable phone ownership or data allowances, so tools that demand
connectivity inadvertently exclude the most vulnerable.[3][4][11]
The IVR service 321 (Viamo, Burkina Faso) works on any phone (feature phone or
smartphone) via voice call, making it one of the few truly accessible platforms in the
country.[3]
M-Shamba uses SMS and IVR in addition to apps, achieving broader reach than apponly competitors.[1][4]
Gap 4: Tools Are Not Usable on Low-End Phones or in Offline Mode,
Excluding Most Rural Farmers
Most platforms built by startups or tech teams in capital cities default to app-only,
inadvertently excluding rural users.[1][4][11]
A 2023 Rethink Priorities report on weather forecasting noted that global weather
models' accuracy remains poor in low-income regions; local offline calculation and
caching could improve usability, but this is rarely implemented.[8]
1. Offline-first architecture: the app downloads essential data (planting calendar,
pest/disease ID database, input prices) weekly via WiFi or when signal is available; all
core features work without connectivity.
2. SMS and voice IVR fallback: if the app does not load, critical advisory (e.g., "Rain
forecast: plant tomorrow") goes via SMS or a 30-second voice call.
## 3. Low-specification design: the app runs on phones with 512 MB–1 GB RAM and
Android 5.0+, not just flagship devices.
4. Data efficiency: the app uses < 5 MB per month of data; compression, chunking, and
selective sync reduce bandwidth demand.
5. Local content hosting: instead of fetching from distant servers, district extension
offices or mobile operators cache locally relevant content (local prices, regional
pests, proven practices).
Most digital agriculture tools are designed in English or French, with limited or no
translation to local languages. Burkina Faso has five national languages (Moore, Dioula,
Fulfuldé, Léle, and French) plus dozens of minority languages. A farmer who does not speak
French or English fluently will struggle with interfaces, instructions, and agronomic terms
in a foreign language. This is not a matter of "digital literacy"; it is linguistic exclusion.[3][4]
[11]
Even where tools exist in local languages (e.g., the Viamo IVR service in Burkina Faso), the
content is often recorded by non-farmers or urban staff, with terminology or pacing that
does not match how rural farmers discuss crops and problems. A farmer hearing a rapid-
fire technical explanation on a crackling phone line may not retain actionable knowledge.
[3][4][11]
Additionally, many platforms are designed with the assumption that farmers are literate.
Even where literacy rates have improved, many rural farmers, especially women and
elders, prefer oral communication. Platforms that rely on text-based interfaces, written
instructions, or assumption of formal education exclude large populations.[1][4][11]
If a farmer hears advisory in a language they do not speak fluently, they will not trust the
advice, will not remember the details, and will not adopt the recommended practice.
Language is not a "nice-to-have" for inclusion; it is a core requirement for effectiveness.[3]
[4][11]
Gap 5: Language Localization Is Minimal; Tools Serve Elite/Educated Users,
Not Majority Farmers
Moreover, solutions marketed as "using AI for local languages" (e.g., "trained on 50,000
Swahili sentences") rarely account for agronomic dialect: the words farmers use to describe
a crop, a pest, or a soil condition are often not the formal academic terms. A farmer says
"millet is yellow" (a sign of nitrogen deficiency); the AI expects "chlorosis" or "nitrogen
deficiency." The mismatch causes failure.[1][4][11]
Viamo's 321 IVR in Burkina Faso operates in five national languages (Moore, Dioula,
Fulfuldé, Léle, French), achieving ~130,000–150,000 calls per month. This is one of the
strongest examples of language-localized advisory in the region.[3]
Crop2Cash in Nigeria trains its AI models in seven local languages, including Yoruba
and Igbo, and has seen success with smallholder uptake. However, scaling this
approach requires significant investment per language and region.[1][4]
Most web-based platforms (e.g., from startups, tech hubs) default to English or
French, with token translations if any.[1][4][11]
Radio remains popular for agricultural extension, but presenter expertise in farming
is often limited. Community radio can be a vector for local-language advisory if
content is co-produced with extension agents and farmers.[3][4][11]
1. Participatory content design: farmers, extension agents, and researchers co-create
advisory content in local languages, recording farmers' own voices and terminology.
2. Voice-first interfaces: the platform prioritizes audio (voice calls, voice messages,
audio snippets) over text, with local-language speakers narrating and explaining
recommendations.
## 3. Community radio integration: short (2–3 minute) audio segments broadcast on
community radio weekly, covering seasonal pests, planting dates, input sourcing,
and market information in local languages.
4. Farmer feedback loops: if a recorded message is unclear, farmers call a toll-free
number and report problems; content is re-recorded and re-tested.
5. Collaboration with local language experts and linguists to ensure terminology
matches how farmers actually speak about crops and problems.
A recurring theme across discussions with West African farmers, extension workers, and
agripreneurs is that tools are designed with assumptions that do not match on-farm reality.
[1][4][11]
## 2. The Gap Between Farmer-Perceived Problems and Tool
Designers' Assumptions
Designer
Assumption Farmer Reality Impact
Farmers want
to optimize
yield at all
costs.
Farmers prioritize food
security and stable
income; risk aversion is
rational, not a barrier to
overcome.
Tools framed as
"maximize yield 20%"
may not fit farmer
priorities if they
increase variability or
input cost.
Better data
leads to better
decisions.
Farmers already make
decisions based on deep
local knowledge; they
want to integrate new
information, not replace
intuition.
Tools that ignore
farmer knowledge or
present contradictory
advice are distrusted.
Digital tools
are cheaper
than extension
agents.
Digital tools are only
useful if they answer
questions extension agents
currently cannot address
or answer faster/more
frequently.
Farmers want
extension agents +
digital tools, not one
or the other.
Farmers will
upgrade their
phones for an
app.
Farmers invest in what is
economically rational for
them. A $100 smartphone
is not justified for one
feature.
Tools must work on
the phone farmers
already own and can
afford.
One
recommendati
on fits all
farmers in a
region.
Farmers are highly
differentiated by wealth,
land size, family labor, soil,
water access, and
priorities. Generic advice
fails frequently.
Segmentation and
adaptive
recommendations are
essential, not nice-tohave.
Weather
forecasts are
useful if they
are "more
accurate than
random."
Farmers need forecasts
accurate to ± 5 days and
localized to their village;
coarse accuracy at
national scale is less
useful.
Seasonal forecasts (3
months ahead) are
useful for planning;
daily forecasts matter
for immediate
decisions.
1. Start with farmer co-design, not technology. Before coding, spend 2–3 months in
the target communities observing decision-making, listening to problems, and
prototyping low-tech solutions (paper cards, radio, SMS). Only then build digital tools.
## 2. Build offline-first and SMS-first, not app-first. Assume users have 2G and
intermittent signal. Design so that the app works without connectivity, and critical
information flows via SMS or voice calls.
3. Localize to real farmer language, not formal academic terms. Record advisory in
farmers' own voices using their terminology. Test with target farmers; if they cannot
understand a message, re-record it.
4. Integrate with existing extension systems, not replace them. Digital tools should
amplify extension agents' reach (e.g., SMS updates that agents reference in group
meetings), not displace them. Agents need training on the tool and buy-in that it is a
complement.
5. Build feedback loops and iterate quickly. Deploy early and with small cohorts;
measure adoption, trust, and behavior change; adjust content and design rapidly. A
tool that works for 10 farmers can be scaled; a tool that does not earn trust from the
first 10 will fail.
6. Partner with national research and extension institutions from day one. Content
credibility depends on endorsement by respected agronomists and extension
services. Government endorsement also signals sustainability and scale.
7. Monetize responsibly. Free tools to farmers; charge government agencies, NGOs, or
private companies that benefit from aggregate insights or market linkages. Do not
put the cost on the farmer.
1. Map the digital landscape locally. Conduct an audit of what tools already exist in
your region, what works, what fails, and why. Do not assume new tools are better;
often, combinations of existing tools (radio + SMS + extension agent visits) are most
effective.
2. Train extension agents on digital advisory platforms. If a government or NGO is
promoting a digital tool, fund training for the extension workers who will support it.
An untrained extension worker cannot explain the tool to farmers.
3. Invest in agro-meteorological content and dissemination. National meteorology
agencies (ANAM in Burkina Faso, ASECNA in Sahel) produce valuable forecasts but
disseminate them poorly. Invest in SMS/IVR translation to local languages and
regular farmer feedback on forecast accuracy.
## 4. Support soil testing and agronomic trial networks. Encourage farmers and
research stations to conduct on-farm trials of varieties and practices in your zone.
Farmers are more likely to trust advisory based on trials they see (neighboring
farms) than distant research results.
## 5. Regulate and accredit digital agriculture services. If companies are selling
advisory services to farmers, ensure a basic standard: accuracy claims are disclosed,
feedback mechanisms exist, and farmers have recourse if advice fails.
## 3. Opportunities for Improvement: Actionable
Recommendations
For Tool Developers and Tech Teams
For Extension Services and Government
## 6. Create incentives for tool developers to localize. Public procurement or
subsidized licensing can make localization economically viable for small teams. A
tool that works in English but not Moore is a failed investment if the target farmer
speaks Moore.
1. Approach digital tools with healthy skepticism. Before adopting a new tool, ask: Is
this answering a real problem I have? Can I understand how it works? Is it affordable
in time and money? Can I revert to my old method if the tool fails?
## 2. Demand local relevance. If a tool does not work on your phone, or does not
mention the crops you grow, or is in a language you do not speak, do not adopt it. Tell
the tool provider why it failed.
3. Test on a small plot first. Do not change your entire farming practice based on
advisory from a tool you have never used. Test on a small area (even 10 m²) for one
season.
## 4. Combine digital advice with human advice. Talk to your neighbors, your
extension agent, and your farmer association. If digital advice contradicts trusted
local knowledge, dig deeper before adopting.
5. Share feedback and failures. If a tool's advice fails, report it. If it works,
recommend it. Word-of-mouth is how farmers decide; tool providers cannot improve
if they do not hear about failures.
6. Organize into groups to reduce cost and increase influence. A farmer association
has more bargaining power with tool providers, can negotiate better pricing, and can
collectively demand localization and support.
The most successful agricultural advisory systems in West Africa are hybrid:
National and regional meteorology: official forecasts, validated but coarse.
Extension agents: trained, trusted, know farmers personally, but limited reach and
frequency.
Digital tools (SMS, IVR, radio): high reach, low cost, but impersonal and sometimes
inaccurate.
Farmer networks: word-of-mouth, peer learning, most trusted, but narrow
geographic reach.
Effective systems layer these:
## 1. National Met Service produces seasonal and medium-range forecasts (done
monthly and weekly).
2. District Extension Office interprets forecasts for local context, identifies priority
pests, and updates agro-meteorological bulletins (done every 10 days).
3. IVR/SMS provider (e.g., Viamo or similar) disseminates bulletins in local languages
via automated calls and SMS (done 3× per week during growing season).
4. Radio stations broadcast summaries and highlight key decisions farmers face that
week (done 2× per week).
For Farmers and Farmer Groups
## 4. Integrating Digital Tools with Traditional Extension: A
Model
5. Extension agents facilitate group meetings where farmers discuss forecasts, test
results, and plan activities together (done every 1–2 weeks during growing season).
## 6. Farmer WhatsApp groups and informal networks amplify and contextualize
messages (continuous).
This model has been implemented in parts of Senegal, Kenya, and Zambia with modest but
measurable results (10–20% adoption of recommended practices, 5–15% yield increases for
early adopters). The key is that all layers reinforce each other, and no single tool is expected
to replace the others.[1][3][4]
Digital agriculture tools are not panaceas; they are tools. Their effectiveness depends not
on their sophistication but on how well they solve real problems for real farmers at prices
and accessibility farmers can afford.
The gaps documented in this report—unreliable weather, generic crop advice, inaccessible
interfaces, offline limitations, and language exclusion—are not insurmountable. Many are
being addressed piecemeal by practitioners in the region. The Viamo 321 service in Burkina
Faso shows that IVR in local languages can reach >100,000 farmers monthly. Platforms like
M-Shamba and Complete Farmer demonstrate that SMS + voice can deliver more localized
advice. On-farm trial networks and farmer-led research show that localized agronomic
knowledge is accessible and motivating.
What is missing is systematic integration: combining what works (extension agents, local
radio, farmer groups) with what is new (AI disease diagnosis, satellite rainfall data, market
price information) in a design that respects farmer knowledge, works on the phones and
connectivity farmers actually have, and is delivered in languages farmers speak.
For Burkina Faso and West Africa specifically, priorities are:
1. Strengthen agro-meteorological content in local languages through IVR and radio,
with monthly farmer feedback on forecast accuracy.
2. Conduct farmer-validated agronomy trials for key crops in each agroecological zone,
generating rules-based advisory that extension agents and digital tools can
reference.
## 3. Develop affordable, crowdsourced disease and pest diagnostics using farmer
photography and expert validation, tailored to Sahel crops.
4. Invest in offline-first, SMS-enabled platforms that work on feature phones and basic
smartphones, avoiding app-only designs.
## 5. Establish a regional digital agriculture coordination mechanism (ECOWAS or
national governments) to share tools, standards, and localized content across
countries, avoiding reinvention.
The opportunity is real. Digital tools, designed with farmers rather than for them, and
integrated with strong extension systems and farmer networks, can improve yields, reduce
risk, and strengthen resilience in the face of climate change. The gap between ambition and
reality can close—but only if tool designers listen, farmers test and feedback, and
institutions commit to the longer journey of implementation, learning, and adaptation.
## 5. Conclusion: The Path Forward
[1] CEIMIA (International Centre of Expertise in Montreal on Artificial Intelligence). (2024).
State of AI in Agriculture in Sub-Saharan Africa. https://zenodo.org/record/13144813
[2] IDinsight. (2024). Making Digital Tools Work for Farmers in Africa. Retrieved from http
s://www.idinsight.org/publication/making-digital-tools-work-for-farmers-in-africa/
[3] Development Gateway & IFAD. (2023). Case Study: Improving Climate Change Resilience
and Market Access Through Digital Services in Burkina Faso. IFAD DAS Program.
[4] Brookings Institution. (2022). Overcoming the Barriers to Technology Adoption on
African Farms. Retrieved from https://www.brookings.edu/articles/overcoming-the-barriers
-to-technology-adoption-on-african-farms/
[5] Rethink Priorities. (2024). Better Weather Forecasting: Impacts on Agriculture in Lowand Lower-Middle-Income Countries. Retrieved from https://rethinkpriorities.org/publicatio
ns
[6] World Bank. (2024). From Fields to Markets: The Role of Digital Platforms in West
Africa's Agriculture. https://projects.worldbank.org/en/results/2025/03/04/afw-from-fields-tomarkets-the-role-of-digital-platforms-in-west-africa-agriculture
[7] Frontiers in Water. (2025). Seasonal Prediction of Rainfall Variability for the West
African Sudan-Sahel Region: A Multi-Model Assessment. https://www.frontiersin.org/journal
s/water/articles/10.3389/frwa.2024.1523898
[8] Deutsche Welle (DW). (2024). The Race to Fix Africa's Poor Weather Forecasting.
Retrieved from https://www.dw.com/en/the-race-to-x-africas-poor-weather-forecasting/a-6
9081374
[9] IFAD. (2023). Programme to Strengthen Smallholder Resilience (PSSR) Concept Note.
Retrieved from institutional sources.
[10] International Centre for Research in Arid and Semi-Arid Lands (ICRISAT). West Africa
Seasonal Surveillance (WAS-S2S) project documentation.
[11] Frontiers in Sustainable Food Systems. (2025). Challenges and Opportunities in
Smallholder Agriculture Digitization. https://www.frontiersin.org/journals/sustainable-foodsystems/articles/10.3389/fsufs.2025.1583224
[12] CIP (International Potato Center). (2020). Smartphone-Based Diagnosis of Crop
Diseases: AI-Based Mobile Phone Apps for Farmers in Africa. https://cipotato.org/cip_project
s/smartphone-based-diagnosis-crop-diseases/
[13] National Center for Biotechnology Information (NCBI). (2023). mPD-APP: A MobileEnabled Plant Diseases Diagnosis Application for Sub-Saharan Africa. PMC10561242. https://
pmc.ncbi.nlm.nih.gov/articles/PMC10561242/
References

## Tables extraites


| Designer Assumption | Farmer Reality | Impact |
| --- | --- | --- |
| Farmers want to optimize yield at all costs. | Farmers prioritize food security and stable income; risk aversion is rational, not a barrier to overcome. | Tools framed as "maximize yield 20%" may not fit farmer priorities if they increase variability or input cost. |
| Better data leads to better decisions. | Farmers already make decisions based on deep local knowledge; they want to integrate new information, not replace intuition. | Tools that ignore farmer knowledge or present contradictory advice are distrusted. |
| Digital tools are cheaper than extension agents. | Digital tools are only useful if they answer questions extension agents currently cannot address or answer faster/more frequently. | Farmers want extension agents + digital tools, not one or the other. |
| Farmers will upgrade their phones for an app. | Farmers invest in what is economically rational for them. A $100 smartphone is not justified for one feature. | Tools must work on the phone farmers already own and can afford. |
| One recommendati on fits all farmers in a region. | Farmers are highly differentiated by wealth, land size, family labor, soil, water access, and priorities. Generic advice fails frequently. | Segmentation and adaptive recommendations are essential, not nice-to- have. |
| Weather forecasts are useful if they are "more accurate than random." | Farmers need forecasts accurate to ± 5 days and localized to their village; coarse accuracy at national scale is less useful. | Seasonal forecasts (3 months ahead) are useful for planning; daily forecasts matter for immediate decisions. |
