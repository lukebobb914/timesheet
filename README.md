
# Timesheet Tracking

> This repository contains programs to track timesheets including tracking OT hours using streamlit.

[![Open App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://timesheet-3wmj5hft2wxvvsqzk4dybm.streamlit.app/)

## Assumptions 
There are some assumptions made in this calculator and are presented below: 
1. OT is counted at 1.5X and starts counting after a workday exceeds 8h 
2. OT is banked until capped at 80h and is then paid out 
3. If OT bank is already at cap, banked OT that is taken will first consume any earned OT during that pay period prior to being paid out  

## Installation

### Clone Repo  

```bash  
git clone ...
```

### Create Virtual Environemnt  

```bash
uv sync
source .venv/bin/activate
```

## Project Structure

```
base_dev/
│
├── pyproject.toml          # Project dependencies
├── uv.lock                 # Locked dependency versions
├── README.md               # Instructions
├── scripts/
│   ├── app.py              # streamlit app 
│   ├── ot_tracker.py        # ot tracker function
└── .venv/                  # Virtual environment (created automatically)
```
