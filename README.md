# Rebel Factionalization and Conflict Duration

*How Does Rebel Factionalization Shape Conflict Duration? Evidence from a Natural Experiment in Northeast India, 1966-2022.*

The two insurgencies have similar structures, but there is one major difference: Mizoram enjoyed a single channel of negotiations, resulting in a durable peace agreement in 1986, whereas Nagaland was subject to fragmentation-and-containment strategy for a whopping period of 75 years. We compute a Rebel Cohesion Index and apply it to the MHA dataset; a one SD decrease in cohesion is associated with 33.7% more incidents annually.

## Structure
```
main_area/         paper and math appendix (LaTeX)
data/              nagaland_mizoram.json
research_tools/    analysis code and scratch work
dist/              compiled PDF
Makefile           local build
```
## Running it
```bash
pip install numpy scipy statsmodels matplotlib
cd research_tools
python3 analysis.py
```

Loads the JSON, verifies every number in the paper, runs the regressions, builds the figures.

`toolkit.py` is case-agnostic (OFS, IVR, CPC, NegBin, ITS, mediation). `analysis.py` applies it to the India case.
## Data

- MHA Nagaland and Mizoram: [NE Insurgency profile (2023)](https://www.mha.gov.in/sites/default/files/2023-03/NE_Insurgency_profile.pdf)
- Mizoram pre-1999: Bhaumik (2009), Choudhury (1999)
- Faction data: [SATP](https://www.satp.org)
- NSDP: RBI Handbook
## Build

```bash
make          # main paper
make appendix # math appendix
```
CI rebuilds the PDF on push.
