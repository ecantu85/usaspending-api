from elasticsearch_dsl import A
from rest_framework.response import Response
from usaspending_api.agency.v2.views.agency_base import AgencyBase
from usaspending_api.common.cache_decorator import cache_response
from usaspending_api.common.elasticsearch.search_wrappers import TransactionSearch
from usaspending_api.common.query_with_filters import QueryWithFilters


class Awards(AgencyBase):
    """
    Returns award and transaction information for USAspending.gov's Agency Details page for agencies
    that have ever awarded.
    """

    endpoint_doc = "usaspending_api/api_contracts/contracts/v2/agency/toptier_code/awards.md"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params_to_validate = ["fiscal_year", "award_type_codes", "agency_type"]

    @cache_response()
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "fiscal_year": self.fiscal_year,
                "toptier_code": self.toptier_agency.toptier_code,
                "transaction_count": self.get_transaction_count(),
                "obligations": self.get_obligations(),
                "messages": self.standard_response_messages,
            }
        )

    def generate_query(self):
        return {
            "agencies": [
                {"type": self._query_params.get("agency_type"), "tier": "toptier", "name": self.toptier_agency.name}
            ],
            "time_period": [{"start_date": f"{self.fiscal_year - 1}-10-01", "end_date": f"{self.fiscal_year}-09-30"}],
            "award_type_codes": self._query_params.get("award_type_codes", []),
        }

    def get_transaction_count(self):
        filter_query = QueryWithFilters.generate_transactions_elasticsearch_query(self.generate_query())
        search = TransactionSearch().filter(filter_query)
        results = search.handle_count()
        return results

    def get_obligations(self):
        filter_query = QueryWithFilters.generate_transactions_elasticsearch_query(self.generate_query())
        search = TransactionSearch().filter(filter_query)
        search.aggs.bucket("total_obligation", A("sum", field="generated_pragmatic_obligation"))
        response = search.handle_execute()
        results = round(response.aggs.to_dict().get("total_obligation", {}).get("value", 0), 2)
        return results