from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.operators.latest_only_operator import LatestOnlyOperator

from dashboard_subdags import parallel_subdag, monthly_subdag, run_query_template

default_args = {
    'owner': 'cchq',
    'depends_on_past': False,
    'start_date': datetime(2019, 7, 01),
    'email': ['{}@{}'.format(name, 'dimagi.com') for name in ('dashboard-aggregation-script',)],
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 3,
    'retry_delay': timedelta(minutes=15),
}

DASHBOARD_DAG_ID = 'dashboard_aggregation'

dashboard_dag = DAG(DASHBOARD_DAG_ID, default_args=default_args, schedule_interval='0 18 * * *')

setup_aggregation = BashOperator(
    task_id='setup_aggregation',
    bash_command=run_query_template,
    params={'query': 'setup_aggregation', 'interval': '0'},
    dag=dashboard_dag
)

prev_month = SubDagOperator(
    subdag=monthly_subdag(
        DASHBOARD_DAG_ID,
        'prev_month',
        dashboard_dag.default_args,
        dashboard_dag.schedule_interval,
        '-1'
    ),
    task_id='prev_month',
    dag=dashboard_dag
)

current_month = SubDagOperator(
    subdag=monthly_subdag(
        DASHBOARD_DAG_ID,
        'current_month',
        dashboard_dag.default_args,
        dashboard_dag.schedule_interval,
        '0'
    ),
    task_id='current_month',
    dag=dashboard_dag
)

aggregate_awc_daily = BashOperator(
    task_id='aggregate_awc_daily',
    bash_command=run_query_template,
    params={'query': 'aggregate_awc_daily', 'interval': '0'},
    dag=dashboard_dag
)

setup_aggregation >> prev_month >> current_month >> aggregate_awc_daily
