# -*- coding: utf-8 -*-
"""
Created on Fri Jul  2 16:24:18 2021

@author: drhyd
"""

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from py2neo import Graph
import pandas as pd
import plotly.express as px
from datetime import date

graph = Graph("http://localhost:7474", auth=("neo4j", "44444444"), name = "ditchleyrere")

app = dash.Dash(__name__)
app.layout = html.Div(
    children = [
        html.Div(
            children = html.H1(
                children = "Ditchley Analytics", style = {'textAlign': 'center'}, className = "header-title"
            ),
            className = "page-header"
        ),
        html.Div(
            children = [
                html.Div(children = 'Year', style = {'fontSize': "24px"}, className = 'menu-title'),
                dcc.Dropdown(
                    id = 'year-filter',
                    placeholder = "Select a year",
                    options = [
                        {'label': Year, 'value': Year}
                        for Year in [2015, 2016, 2017, 2018, 2019, 2020]
                    ],
                    clearable = False,
                    searchable = False,
                    className = 'dropdown',
                    style = {'fontSize': "24px",'textAlign': 'center'}
                ),
                html.Div(children = 'Date Range', style = {'fontSize': "24px"}, className = 'menu-title'),
                dcc.DatePickerRange(
                    id = 'date-picker-range',
                    min_date_allowed = date(2000, 1, 1),
                    max_date_allowed = date(2021, 6, 1),
                    initial_visible_month = date(2021, 5, 1),
                    clearable = True
                )
            ],
            className = 'menu'
        ),

        html.Div(
            children = [
                html.Div(
                    children = html.H1(
                        id = 'metrics-title', style = {'textAlign': 'center'}, className = "header-title"
                    ),
                    className = "figure-header"
                ),
                html.Div(
                    children = dcc.Graph(
                        id = 'country-plot'
                    ),
                    style = {'width': '50%', 'display': 'inline-block'}
                ),
                html.Div(
                    children = dcc.Graph(
                        id = 'gender-plot'
                    ),
                    style = {'width': '50%', 'display': 'inline-block'}
                ),
                html.Div(
                    children = [
                        dcc.Graph(
                            id = 'org-sector-plot'
                        ),
                        # dcc.Dropdown(
                        #     id = 'org-sector-filter',
                        #     placeholder = "Select an org sector",
                        #     options = [],
                        #     clearable = False,
                        #     searchable = True,
                        #     className = 'dropdown',
                        #     style = {'fontSize': "18px",'textAlign': 'center'}
                        # )
                    ],
                    style = {'width': '50%', 'display': 'inline-block'}
                ),
                html.Div(
                    children = dcc.Graph(
                        id = 'new-comers-plot'
                    ),
                    style = {'width': '50%', 'display': 'inline-block'}
                )
            ],
            className = 'double-graph'
        )
    ]
)

@app.callback(
    Output("metrics-title", "children"),
    Output("country-plot", "figure"),
    Output("gender-plot", "figure"),
    Output("org-sector-plot", "figure"),
    Output("new-comers-plot", "figure"),
    # Output("org-sector-filter", "options"),
    [Input("year-filter", "value"),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update(year, start_date, end_date):
    ctx = dash.callback_context
    response = None
    if ctx.triggered:
        trig = ctx.triggered[0]['prop_id'].split('.')[0]
        if trig == "year-filter":
            response = updateByYear(year)
        elif trig == "date-picker-range":
            if start_date and end_date:
                response = updateByDateRange(start_date, end_date)
    return response[0], response[1], response[2], response[3], response[4]

def updateByYear(year):
    data_for_year = graph.run("""
                                  match (e:DitchleyEvent)<-[r:PARTICIPATED_IN]-(p:DitchleyPerson)
                                  where e.start_date.year = """ + str(year) + """
                                  optional match (p)-[t:PARTICIPATED_IN]->(f:DitchleyEvent)
                                  where f.start_date < e.start_date
                                  optional match (p)-[s:HAS_POSITION]->(c:DitchleyCompany)
                                  with distinct p.full_name as Full_name, p.gender as Gender, p.represents as Country, c.name as Org_name, c.industry_category as Org_sector, count(distinct e.name) as count_curr, count(distinct f.name) as count_prev
                                  where Org_name IS NULL OR Org_name <> "The Ditchley Foundation"
                                  return Full_name, Gender, Country, Org_sector, count_curr, count_prev
                                  order by count_prev desc
                              """).to_data_frame().replace("", "Unknown")
    events_count = graph.run("""
                                 match (e:DitchleyEvent)
                                 where e.start_date.year = """ + str(year) + """
                                 return count(e) as count
                             """).to_data_frame()["count"][0]

    metricsTitle = str(year) + " metrics; Total participants: " + str(len(data_for_year)) + "; No. of events: " + str(events_count)

    country_series = data_for_year.value_counts(subset = "Country").head(20)
    country_df = pd.DataFrame({"Country": country_series.index, "count": country_series.values}).sort_values("count", ascending = True)
    hbarsCountry = px.bar(country_df, y="Country", x="count", orientation='h', text='count', title='Location distribution - Top 20', labels={
        "count": "Number of participants"
    })
    hbarsCountry.update_layout(
        yaxis = dict(
            dtick = 1
        )
    )

    gender_series = data_for_year.value_counts(subset = "Gender")
    gender_df = pd.DataFrame({"Gender": gender_series.index, "percent": gender_series.values * 100/gender_series.sum()}).sort_values("percent", ascending = True)
    hbarsGender = px.bar(gender_df, y="Gender", x="percent", orientation='h', text='percent', title='Gender distribution', hover_data = {'percent': ':.2f'}, labels={
        "percent": "% of participants"
    })
    hbarsGender.update_traces(texttemplate='%{text:.2f}')

    org_sector_series = data_for_year.value_counts(subset = "Org_sector").head(20)
    org_sector_df = pd.DataFrame({"Org_sector": org_sector_series.index, "count": org_sector_series.values}).sort_values("count", ascending = True)
    hbarsOrgSector = px.bar(org_sector_df, y="Org_sector", x="count", orientation='h', text='count', title='Industry distribution - Top 20', labels={
        "count": "Number of participants",
        "Org_sector": "Organization sector"
    })
    hbarsOrgSector.update_layout(
        yaxis = dict(
            dtick = 1
        )
    )

    data_for_year['count_prev'].where(data_for_year['count_prev'] < 10, 10, inplace=True)

    count_prev_series = data_for_year.value_counts(subset = "count_prev")
    count_prev_df = pd.DataFrame({"count_prev": count_prev_series.index, "count": count_prev_series.values}).sort_values("count_prev", ascending = True)
    yValues = count_prev_df["count_prev"].astype(str).tolist()
    yValues[-1] += "+"
    count_prev_df["yValues"] = yValues
    hbarsNewComers = px.bar(count_prev_df, y="yValues", x="count", orientation='h', text='count', title='New comer distribution', labels={
        "count": "Number of participants",
        "yValues": "Number of prior events (events + conferences)"
    })
    
    return metricsTitle, hbarsCountry, hbarsGender, hbarsOrgSector, hbarsNewComers

def updateByDateRange(start_date, end_date):
    org_sector_set = set({})
    
    events_df = graph.run("""
                              match (e:DitchleyEvent)
                              where e.start_date > date('""" + start_date + """') and e.start_date < date('""" + end_date + """')
                              return e.id as id, e.name as name, e.type as type, e.start_date as date
                              order by date desc
                          """).to_data_frame()
    
    for event_id in events_df["id"]:
        participants_df = graph.run("""
                                        match (e:DitchleyEvent)<-[r:PARTICIPATED_IN]-(p:DitchleyPerson)
                                        where e.id = '""" + event_id + """'
                                        optional match (p)-[s:PARTICIPATED_IN]->(f:DitchleyEvent)
                                        where f.start_date < e.start_date
                                        optional match (p)-[t:HAS_POSITION]->(c:DitchleyCompany)
                                        optional match (p)-[u:WORKS_IN_CITY]->(ct:City)-[v:IN_COUNTRY]->(cn:Country)
                                        with distinct p.full_name as Full_name, p.gender as Gender, p.represents as Country_Rep, cn.country as Country_Wrk, ct.city as City, c.name as Org_name, c.industry_category as Org_sector, count(distinct e.name) as count_curr, count(distinct f.name) as count_prev
                                        where Org_name IS NULL OR Org_name <> "The Ditchley Foundation"
                                        return Full_name, Gender, Country_Rep, Country_Wrk, City, Org_sector, count_curr, count_prev
                                        order by count_prev desc
                                    """).to_data_frame().replace("", "Unknown")
        
        if(participants_df.empty == False):
            gender_series = participants_df.value_counts(subset = "Gender")
            count_prev_series = participants_df.value_counts(subset = "count_prev")
            org_sector_series = participants_df.value_counts(subset = "Org_sector")
            org_sector_set.update(org_sector_series.index.tolist())
            uk_participants_df = participants_df.loc[participants_df["Country_Wrk"] == "United Kingdom"]
            city_series = uk_participants_df.value_counts(subset = "City")
            if("Female" in gender_series.index):
                if("Unknown" in gender_series.index):
                    events_df.loc[events_df["id"] == event_id, ["f_percent"]] = gender_series["Female"] * 100 / (gender_series.sum() - gender_series["Unknown"])
                else:
                    events_df.loc[events_df["id"] == event_id, ["f_percent"]] = gender_series["Female"] * 100 / gender_series.sum()
            if(0 in count_prev_series.index):
                events_df.loc[events_df["id"] == event_id, ["first_time_pc"]] = count_prev_series[0] * 100 / count_prev_series.sum()
            if("Media" in org_sector_series.index):
                events_df.loc[events_df["id"] == event_id, ["media_pc"]] = org_sector_series["Media"] * 100 / org_sector_series.sum()
            if(city_series.empty == False):
                events_df.loc[events_df["id"] == event_id, ["outside_london_pc"]] = city_series.loc[city_series.index != "London"].sum() * 100 / city_series.sum()
            events_df.loc[events_df["id"] == event_id, ["count_participants"]] = gender_series.sum()
    
    metricsTitle = "Metrics for events between " + start_date + " and " + end_date + "."
    
    fig_gender = px.scatter(data_frame = events_df, x = "date", y = "f_percent", color = "type", hover_name = "name", hover_data = ["count_participants"], labels = {
        "date": "Date",
        "f_percent": "Percentage of Female participants",
        "type": "Type of event"
    })
    
    fig_count_prev = px.scatter(data_frame = events_df, x = "date", y = "first_time_pc", color = "type", hover_name = "name", hover_data = ["count_participants"], labels = {
        "date": "Date",
        "first_time_pc": "Percentage of first timers",
        "type": "Type of event"
    })
    
    fig_org_sector = px.scatter(data_frame = events_df, x = "date", y = "media_pc", color = "type", hover_name = "name", hover_data = ["count_participants"], labels = {
        "date": "Date",
        "media_pc": "Percentage of participants from the media",
        "type": "Type of event"
    })
    
    fig_city = px.scatter(data_frame = events_df, x = "date", y = "outside_london_pc", color = "type", hover_name = "name", hover_data = ["count_participants"], labels = {
        "date": "Date",
        "outside_london_pc": "Percentage of participants from outside London",
        "type": "Type of event"
    })
    
    org_sector_options = [
        {'label': org_sec, 'value': org_sec}
        for org_sec in sorted(org_sector_set)
    ]
    
    return metricsTitle, fig_city, fig_gender, fig_org_sector, fig_count_prev, org_sector_options

if __name__ == '__main__':
    app.run_server()