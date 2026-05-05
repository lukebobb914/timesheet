# =============================================================================
# Current Author   : Michael Chan
# Contact Info     : mchan@core6.ca
#
# This is a ot tracker based on timesheet entries from CORE
#
# ============================================================================

# %%
import pandas as pd

def track_ot(file) -> pd.DataFrame: 
    # ===============================
    # import/clean
    # ===============================
    df = pd.read_csv(file, encoding='cp1252')
    df.columns = df.columns.str.lower()
    df['date'] = pd.to_datetime(df['date'])

    # ===============================
    # split data
    # ===============================
    is_banked = df['description'].str.contains('Banked Time', case=False, na=False)

    worked_df = df[~is_banked]   # hours that generate OT
    used_df = df[is_banked]    # hours that consume OT


    # ===============================
    # create daily df 
    # ===============================
    daily = worked_df.groupby('date', as_index=False)['hours'].sum()
    is_weekday = daily['date'].dt.weekday < 5                                               # create weekday mask 
    daily['ot_hours'] = daily['hours']                                                      # initialize OT col 
    daily.loc[is_weekday, 'ot_hours'] = (daily.loc[is_weekday, 'hours'] - 8).clip(lower=0)  
    daily['ot_hours_1.5'] = daily['ot_hours'] * 1.5                                         # OT hours are 1.5X 

    # ===============================
    # add banked OT used 
    # ===============================
    used_df = used_df.rename(columns={'hours': 'ot_used'})
    daily = daily.merge(used_df[['date', 'ot_used']], on='date', how='outer')
    daily['ot_used'] = daily['ot_used'].fillna(0)
    daily['date'].duplicated().any()                         # check duplicated dates after merge

    # ===============================
    # clean 
    # ===============================
    daily[['hours', 'ot_hours', 'ot_hours_1.5']] = daily[['hours', 'ot_hours', 'ot_hours_1.5']].fillna(0)
    daily['day'] = daily['date'].dt.day_name()

    # ===============================
    # track usage/consumption with cap
    # ===============================
    # create a net value 
    daily['net_ot'] = daily['ot_hours_1.5'] - daily['ot_used']

    cap = 80
    daily = daily.sort_values('date').reset_index(drop=True)

    balance = 0
    balances = []
    paid_out = []

    for _, row in daily.iterrows():
        balance += row['net_ot']
        
        if balance > cap:
            paid = balance - cap
            balance = cap
        else:
            paid = 0
        
        balances.append(balance)
        paid_out.append(paid)

    daily['ot_balance_capped'] = balances
    daily['ot_paid_out'] = paid_out

    return daily