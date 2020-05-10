# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---



#
# https://www.thelancet.com/journals/lanpsy/article/PIIS2215-0366(20)30171-1/fulltext
#
# https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/deaths/bulletins/deathsrelatedtodrugpoisoninginenglandandwales/previousReleases

#import libraries
from ebmdatalab import bq
from ebmdatalab import charts
from ebmdatalab import maps
import os
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

# +
sql = '''WITH
bnf_tab AS (
SELECT
DISTINCT chemical,
chemical_code
FROM
ebmdatalab.hscic.bnf )
SELECT
rx.month,
rx.pct,
SUBSTR(rx.bnf_code,1,9) AS chemical_code,
chemical,
sum(items) AS total_items,
sum(actual_cost) as total_cost
FROM
hscic.normalised_prescribing_standard AS rx
LEFT JOIN
bnf_tab
ON
chemical_code =SUBSTR(rx.bnf_code,1,9)
JOIN
  hscic.ccgs AS ccgs
ON
rx.pct=ccgs.code
WHERE
  (bnf_code LIKE "0403%" OR ##antidepressants
  bnf_code LIKE "0407010%%" OR ##analgesics
  bnf_code LIKE "0402%") ##antipsychotics
  AND
  bnf_code NOT LIKE "0407010B0%"
  AND
  ccgs.org_type='CCG'
GROUP BY
rx.month,
rx.pct,
chemical_code,
chemical
ORDER BY
month'''

df_poisoning = bq.cached_read(sql, csv_path=os.path.join('..','data','overall_poisoning.csv'))
df_poisoning['month'] = df_poisoning['month'].astype('datetime64[ns]')
df_poisoning.head(3)
# -

df_poisoning.info()

df_poisoning["chemical"].unique()

df_poisoning.groupby("month")['total_items'].sum().plot(kind='line', title="Total number chemicals in ONS report")
plt.ylim(0, )

sql2 = """
SELECT
  month,
  pct_id AS pct,
  SUM(total_list_size) AS list_size
FROM
  ebmdatalab.hscic.practice_statistics
GROUP BY
  month,
  pct
ORDER BY
  month,
  pct,
  list_size
"""
df_list = bq.cached_read(sql2, csv_path=os.path.join('..','data','list_size.csv'))
df_list['month'] = df_list['month'].astype('datetime64[ns]')
df_list.head(3)

ccg_total = df_poisoning.groupby(["month", "pct"])["total_items"].sum().reset_index()
ccg_total.head()

poisoning_ccg_1000 = pd.merge(ccg_total, df_list, on=['month', 'pct'])
poisoning_ccg_1000['items_per_1000'] = 1000* (poisoning_ccg_1000['total_items']/poisoning_ccg_1000['list_size'])
poisoning_ccg_1000.head(3)

# +
#create sample deciles & prototype measure
charts.deciles_chart(
        poisoning_ccg_1000,
        period_column='month',
        column='items_per_1000',
        title="Poisoning items per 1000 (Islington CCG) ",
        show_outer_percentiles=False)

#add in example CCG (Islington)
df_subject = poisoning_ccg_1000.loc[poisoning_ccg_1000['pct'] == '08H']
plt.plot(df_subject['month'], df_subject['items_per_1000'], 'r--')

plt.show()

# +

#create choropeth map of cost per 1000 patients
plt.figure(figsize=(12, 7))
latest_poisoning_df_1000 = poisoning_ccg_1000.loc[(poisoning_ccg_1000['month'] >= '2019-04-01') & (poisoning_ccg_1000['month'] <= '2020-02-01')]
plt = maps.ccg_map(latest_poisoning_df_1000, title="Poisoning items per 1000  \n Apr 2019 - Feb 2020 ", column='items_per_1000', separate_london=True)
plt.show()
# -


