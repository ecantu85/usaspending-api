import copy
import logging

from django.conf import settings
from django.db.models import Func, IntegerField, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from usaspending_api.awards.models_matviews import SummaryAwardRecipientView
from usaspending_api.awards.v2.filters.filter_helpers import combine_date_range_queryset
from usaspending_api.common.cache_decorator import cache_response
from usaspending_api.common.exceptions import InvalidParameterException
from usaspending_api.core.validator.award_filter import AWARD_FILTER
from usaspending_api.core.validator.tinyshield import TinyShield
from usaspending_api.recipient.models import RecipientProfile
from usaspending_api.settings import API_MAX_DATE, API_SEARCH_MIN_DATE

logger = logging.getLogger(__name__)

API_VERSION = settings.API_VERSION


class FiscalMonth(Func):
    function = "EXTRACT"
    template = "%(function)s(MONTH from (%(expressions)s) + INTERVAL '3 months')"
    output_field = IntegerField()


class FiscalQuarter(Func):
    function = "EXTRACT"
    template = "%(function)s(QUARTER from (%(expressions)s) + INTERVAL '3 months')"
    output_field = IntegerField()


class FiscalYear(Func):
    function = "EXTRACT"
    template = "%(function)s(YEAR from (%(expressions)s) + INTERVAL '3 months')"
    output_field = IntegerField()


class NewAwardsOverTimeVisualizationViewSet(APIView):
    """
    endpoint_doc: /advanced_award_search/new_awards_over_time.md
    """

    @cache_response()
    def post(self, request):
        groupings = {
            "quarter": "quarter",
            "q": "quarter",
            "fiscal_year": "fiscal_year",
            "fy": "fiscal_year",
            "month": "month",
            "m": "month",
        }
        models = [
            {"name": "group", "key": "group", "type": "enum", "enum_values": list(groupings.keys()), "default": "fy"},
        ]
        advanced_search_filters = [
            model
            for model in copy.deepcopy(AWARD_FILTER)
            if model["name"] in ("time_period", "recipient_id")
        ]

        for model in advanced_search_filters:
            if model['name'] in ("time_period", "recipient_id"):
                model["optional"] = False
        models.extend(advanced_search_filters)
        json_request = TinyShield(models).block(request.data)
        filters = json_request.get("filters", None)

        if filters is None:
            raise InvalidParameterException("Missing request parameters: filters")

        recipient_hash = filters["recipient_id"][:-2]
        is_parent = True if filters["recipient_id"][-1] == "P" else False
        time_ranges = []
        for t in filters["time_period"]:
            t["date_type"] = "date_signed"
            time_ranges.append(t)
        queryset = SummaryAwardRecipientView.objects.filter()
        queryset &= combine_date_range_queryset(
            time_ranges, SummaryAwardRecipientView, API_SEARCH_MIN_DATE, API_MAX_DATE
        )

        if is_parent:
            # there *should* only one record with that hash and recipient_level = 'P'
            parent_duns_rows = RecipientProfile.objects.filter(
                recipient_hash=recipient_hash, recipient_level="P"
            ).values("recipient_unique_id")
            if len(parent_duns_rows) != 1:
                raise InvalidParameterException("Provided recipient_id has no parent records")
            parent_duns = parent_duns_rows[0]["recipient_unique_id"]
            queryset = queryset.filter(parent_recipient_unique_id=parent_duns)
        else:
            queryset = queryset.filter(recipient_hash=recipient_hash)

        values = ["year"]
        if groupings[json_request["group"]] == "month":
            queryset = queryset.annotate(month=FiscalMonth("date_signed"), year=FiscalYear("date_signed"))
            values.append("month")

        elif groupings[json_request["group"]] == "quarter":
            queryset = queryset.annotate(quarter=FiscalQuarter("date_signed"), year=FiscalYear("date_signed"))
            values.append("quarter")

        elif groupings[json_request["group"]] == "fiscal_year":
            queryset = queryset.annotate(year=FiscalYear("date_signed"))

        queryset = (
            queryset.values(*values).annotate(count=Sum("counts")).order_by(*["-{}".format(value) for value in values])
        )

        results = []
        for row in queryset:
            result = {"time_period": {}}
            for period in values:
                result["time_period"]["fiscal_{}".format(period)] = row[period]
            result["new_award_count_in_period"] = row["count"]

            results.append(result)

        response_dict = {"group": groupings[json_request["group"]], "results": results}

        return Response(response_dict)
