# =============================================================================
# Current Author   : Michael Chan
# Contact Info     : mchan@core6.ca
#
# This is a ot tracker based on timesheet entries from CORE orking version
#
# ============================================================================

# %%
import pandas as pd
from pathlib import Path

# ===============================
# import/clean
# ===============================
data_path = Path.cwd() / 'data'
output_path = Path.cwd() / 'output'
output_path.mkdir(parents=True, exist_ok=True)

# %%
file = data_path / 'Time Entry.csv'
df = pd.read_csv(file)
df.columns = df.columns.str.lower()
df['date'] = pd.to_datetime(df['date'])

# ===============================
# Clean Data
# add back subtracted amounts from banked time
# 1) create a mask for rows with reduction 
# 2) create pd.series with NAF hours
# Pattern explanation:
#   reduced      -> find the word "reduced"
#   \s+          -> one or more spaces
#   (...)        -> capture what is inside the brackets
#   \d+          -> one or more digits (4, 12, 100)
#   (?:\.\d+)?   -> optional decimal part (.5, .50, .75)
# ===============================
mask_regex = r'over 40'         #! ensure this str filters correctly 
naf_mask = df['memo'].str.contains(mask_regex, case=False, na=False)

naf_regex = r'(\d+(?:\.\d+)?)'
naf_value = (
    df.loc[naf_mask, 'memo']
    .str.extract(naf_regex, expand=False)
    .astype(float)
)

df.loc[naf_mask, 'actual hours'] += naf_value
df = df[['date', 'description', 'actual hours']].copy()

# %%
# ===============================
# Create pay period
# ===============================
# * Inputs *
anchor = pd.Timestamp('2025-09-07') #! pay period start date
pay_period_days = 14
pay_period_hours = pay_period_days / 7 * 40                                # get #of weeks multiplied by 40hr week

an_salary = 65000


summary_df = df.groupby('date', as_index=False).agg(total_hours=('actual hours', 'sum'))       # agg hours by day

# ===============================
# create daily worked hrs and ot taken df  
# ===============================
banked_mask = df['description'].str.contains('Banked Time', case=False, na=False)
worked_df = (df.loc[~banked_mask].groupby('date', as_index=False).agg(hours_worked=('actual hours', 'sum')))
used_ot_df = (df.loc[banked_mask].groupby('date', as_index=False).agg(hours_worked=('actual hours', 'sum')))
split_df = worked_df.merge(used_ot_df, on='date', how='outer')      # retain all of worked rows 

# ===============================
# Combine total hours and split df 
# ===============================
summary_df = summary_df.merge(split_df, on='date', how='outer')

summary_df.columns = ['date', 'total_hours', 'hours_worked', 'used_ot']
summary_df['used_ot'] = summary_df['used_ot'].fillna(0)                             # fill nan with 0 
summary_df['hours_worked'] = summary_df['hours_worked'].fillna(0)                   # fill nan with 0 


# ===============================
# Calculate OT hours per pay period 
# ===============================
summary_df['ot_hours'] = (summary_df['hours_worked'] - 8).clip(lower=0) 
summary_df['ot_earned'] = summary_df['ot_hours'] * 1.5                     # OT is 1.5X regular 
summary_df = summary_df.sort_values('date').reset_index(drop=True)
summary_df = summary_df[['date', 'total_hours', 'hours_worked', 'ot_hours', 'ot_earned', 'used_ot']]

#%%
# ===============================
# Sum by pay period 
# ===============================
summary_df['pay_period'] = (anchor + pd.to_timedelta(((summary_df['date'] - anchor).dt.days // pay_period_days) * pay_period_days, unit='D'))
summary_df = summary_df.groupby('pay_period', as_index=False).agg(
    total_hours=('total_hours', 'sum'), 
    hours_worked=('hours_worked', 'sum'), 
    ot_hours=('ot_hours', 'sum'), 
    ot_earned=('ot_earned', 'sum'), 
    used_ot=('used_ot', 'sum'))
summary_df['to_date'] = summary_df['pay_period'] + pd.Timedelta(days=13)
summary_df = summary_df[['pay_period', 'to_date', 'total_hours', 'hours_worked', 'ot_hours', 'ot_earned', 'used_ot']]


#%%
# ===============================
# Calculate banked OT 
# ===============================
ot_bank = 0
cap = 80

net_ot = []
bank_history = []
ot_added = []
ot_paid = []


for _, row in summary_df.iterrows(): 
    total_hours = row['total_hours']    # total hrs entered this period
    ot_earned = row['ot_earned']        # OT earned this period 
    ot_taken = row['used_ot']           # OT taken this period
    net = ot_earned - ot_taken          # net OT 

    # * Prevents adding/removing from banked OT when don't have all data yet for current pay period
    if total_hours < pay_period_hours: # if < pay period hours => don't do anything to bank
        net = 0
        added = 0 
        paid = 0 

        bank_history.append(ot_bank)
        ot_added.append(added)
        ot_paid.append(paid)
        net_ot.append(net)
        continue

    # OT earned > taken 
    if net >= 0: 
        ot_bank += net                  # add net OT to bank 

        # Banked OT exceeds cap 
        if ot_bank > cap:  
            paid = ot_bank - cap        # amt of hours that exceeded 80 hours
            added = net - paid          # amt of hours that could be added to bank
            ot_bank = cap               # update current ot_bank back to cap value 
        # OT bank exactly at cap 
        else: 
            paid = 0
            added = net
    
    # OT earned < taken 
    else: 
        ot_bank += net                  # net is negative
        paid = 0                        # update paid 
        added = 0
        

    # save current pay period's ot_bank, ot added, ot paid out 
    bank_history.append(ot_bank)
    ot_added.append(added)
    ot_paid.append(paid)
    net_ot.append(net)


# add to summary_df 
summary_df['net_ot'] = net_ot
summary_df['ot_added'] = ot_added
summary_df['ot_paid'] = ot_paid
summary_df['ot_bank'] = bank_history

# %%
# ===============================
# Calculate paid out in $
# ===============================
hourly_rate = an_salary/(40*52)     # calculate hourly rate based on 40hr/wk
summary_df['amount_paid_out'] = summary_df['ot_paid'] * hourly_rate

# ===============================
# Calculate total OT hours worked/taken
# ===============================
tot_ot_used = summary_df['used_ot'].sum()
tot_ot_hrs = summary_df['ot_hours'].sum() 
tot_ot_earned = summary_df['ot_earned'].sum()

print(f'Total OT Hours Worked: {tot_ot_hrs}') 
print(f'Total OT Hours Earned {tot_ot_earned}')
print(f'Total Banked OT Taken {tot_ot_used}')
print(f'Current Banked OT Days Available: {ot_bank/8}')

# %%
