from model_mommy import mommy
import pytest


@pytest.fixture
def cfda_awards_and_transactions(db):
    # Awards
    award1 = mommy.make("awards.Award", latest_transaction_id=10, type="07", total_loan_value=3)
    award2 = mommy.make("awards.Award", latest_transaction_id=20, type="07", total_loan_value=30)
    award3 = mommy.make("awards.Award", latest_transaction_id=30, type="08", total_loan_value=300)
    award4 = mommy.make("awards.Award", latest_transaction_id=40, type="02", total_loan_value=0)
    award5 = mommy.make("awards.Award", latest_transaction_id=50, type="A", total_loan_value=0)

    # Disaster Emergency Fund Code
    defc1 = mommy.make(
        "references.DisasterEmergencyFundCode",
        code="L",
        public_law="PUBLIC LAW FOR CODE L",
        title="TITLE FOR CODE L",
        group_name="covid_19",
    )
    defc2 = mommy.make(
        "references.DisasterEmergencyFundCode",
        code="M",
        public_law="PUBLIC LAW FOR CODE M",
        title="TITLE FOR CODE M",
        group_name="covid_19",
    )
    mommy.make(
        "references.DisasterEmergencyFundCode",
        code="N",
        public_law="PUBLIC LAW FOR CODE N",
        title="TITLE FOR CODE N",
        group_name="covid_19",
    )

    # Submission Attributes
    sub1 = mommy.make(
        "submissions.SubmissionAttributes",
        reporting_fiscal_year=2022,
        reporting_fiscal_period=7,
        quarter_format_flag=False,
        is_final_balances_for_fy=False,
        reporting_period_start="2022-04-01",
        submission_window_id=2022070,
    )
    sub2 = mommy.make(
        "submissions.SubmissionAttributes",
        reporting_fiscal_year=2022,
        reporting_fiscal_period=8,
        quarter_format_flag=False,
        is_final_balances_for_fy=True,
        reporting_period_start="2022-05-01",
        submission_window_id=2022080,
    )
    sub3 = mommy.make(
        "submissions.SubmissionAttributes",
        reporting_fiscal_year=2022,
        reporting_fiscal_period=7,
        quarter_format_flag=False,
        is_final_balances_for_fy=False,
        reporting_period_start="2022-04-01",
        submission_window_id=2022070,
    )
    sub4 = mommy.make(
        "submissions.SubmissionAttributes",
        reporting_fiscal_year=9999,
        reporting_fiscal_period=7,
        quarter_format_flag=False,
        is_final_balances_for_fy=False,
        reporting_period_start="9999-04-01",
        submission_window_id=9999070,
    )

    # Financial Accounts by Awards
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=1,
        award=award1,
        submission=sub1,
        disaster_emergency_fund=defc1,
        gross_outlay_amount_by_award_cpe=1,
        transaction_obligated_amount=2,
    )
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=2,
        award=award2,
        submission=sub1,
        disaster_emergency_fund=defc1,
        gross_outlay_amount_by_award_cpe=10,
        transaction_obligated_amount=20,
    )
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=3,
        award=award3,
        submission=sub2,
        disaster_emergency_fund=defc2,
        gross_outlay_amount_by_award_cpe=100,
        transaction_obligated_amount=200,
    )
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=4,
        award=award4,
        submission=sub2,
        disaster_emergency_fund=defc1,
        gross_outlay_amount_by_award_cpe=1000,
        transaction_obligated_amount=2000,
    )
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=5,
        award=award5,
        submission=sub3,
        disaster_emergency_fund=defc2,
        gross_outlay_amount_by_award_cpe=10000,
        transaction_obligated_amount=20000,
    )
    mommy.make(
        "awards.FinancialAccountsByAwards",
        pk=6,
        award=award1,
        submission=sub4,
        disaster_emergency_fund=defc1,
        gross_outlay_amount_by_award_cpe=100,
        transaction_obligated_amount=200,
    )

    # DABS Submission Window Schedule
    mommy.make(
        "submissions.DABSSubmissionWindowSchedule",
        id="2022070",
        is_quarter=False,
        period_start_date="2022-04-01",
        period_end_date="2022-04-30",
        submission_fiscal_year=2022,
        submission_fiscal_quarter=3,
        submission_fiscal_month=7,
        submission_reveal_date="2020-4-15",
    )
    mommy.make(
        "submissions.DABSSubmissionWindowSchedule",
        id="2022080",
        is_quarter=False,
        period_start_date="2022-05-01",
        period_end_date="2022-05-30",
        submission_fiscal_year=2022,
        submission_fiscal_quarter=3,
        submission_fiscal_month=8,
        submission_reveal_date="2020-5-15",
    )
    mommy.make(
        "submissions.DABSSubmissionWindowSchedule",
        id="2022081",
        is_quarter=True,
        period_start_date="2022-05-01",
        period_end_date="2022-05-30",
        submission_fiscal_year=2022,
        submission_fiscal_quarter=3,
        submission_fiscal_month=8,
        submission_reveal_date="2020-5-15",
    )
    # Unclosed submission window
    mommy.make(
        "submissions.DABSSubmissionWindowSchedule",
        id="9999070",
        is_quarter=True,
        period_start_date="9999-04-01",
        period_end_date="9999-04-30",
        submission_fiscal_year=9999,
        submission_fiscal_quarter=3,
        submission_fiscal_month=7,
        submission_reveal_date="9999-4-15",
    )

    # Transaction Normalized
    mommy.make(
        "awards.TransactionNormalized",
        id=1,
        award=award1,
        federal_action_obligation=5,
        action_date="2020-01-01",
        is_fpds=False,
    )
    mommy.make(
        "awards.TransactionNormalized",
        id=10,
        award=award1,
        federal_action_obligation=5,
        action_date="2020-04-01",
        is_fpds=False,
    )
    mommy.make(
        "awards.TransactionNormalized",
        id=20,
        award=award2,
        federal_action_obligation=50,
        action_date="2020-04-02",
        is_fpds=False,
    )
    mommy.make(
        "awards.TransactionNormalized",
        id=30,
        award=award3,
        federal_action_obligation=500,
        action_date="2020-04-03",
        is_fpds=False,
    )
    mommy.make(
        "awards.TransactionNormalized",
        id=40,
        award=award4,
        federal_action_obligation=5000,
        action_date="2020-04-04",
        is_fpds=False,
    )
    mommy.make(
        "awards.TransactionNormalized",
        id=50,
        award=award5,
        federal_action_obligation=50000,
        action_date="2020-04-05",
        is_fpds=True,
    )

    # Transaction FABS
    mommy.make(
        "awards.TransactionFABS", transaction_id=10, cfda_number="10.100",
    )
    mommy.make(
        "awards.TransactionFABS", transaction_id=20, cfda_number="20.200",
    )
    mommy.make(
        "awards.TransactionFABS", transaction_id=30, cfda_number="20.200",
    )
    mommy.make(
        "awards.TransactionFABS", transaction_id=40, cfda_number="30.300",
    )

    # Transaction FPDS
    mommy.make(
        "awards.TransactionFPDS", transaction_id=50,
    )

    # References CFDA
    mommy.make(
        "references.Cfda",
        id=100,
        federal_agency="Agency 1",
        objectives="objectives 1",
        applicant_eligibility="AE1",
        beneficiary_eligibility="BE1",
        program_number="10.100",
        program_title="CFDA 1",
        url="None;",
        website_address=None,
    )
    mommy.make(
        "references.Cfda",
        id=200,
        federal_agency="Agency 2",
        objectives="objectives 2",
        applicant_eligibility="AE2",
        beneficiary_eligibility="BE2",
        program_number="20.200",
        program_title="CFDA 2",
        url="www.example.com/200",
        website_address="www.example.com/cfda_website/200",
    )
    mommy.make(
        "references.Cfda",
        id=300,
        federal_agency="Agency 3",
        objectives="objectives 3",
        applicant_eligibility="AE3",
        beneficiary_eligibility="BE3",
        program_number="30.300",
        program_title="CFDA 3",
        url="www.example.com/300",
        website_address="www.example.com/cfda_website/300",
    )
