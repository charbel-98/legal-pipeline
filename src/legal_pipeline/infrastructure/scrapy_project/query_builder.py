from urllib.parse import urlencode

from legal_pipeline.application.services.search_plan_service import SearchPlan

BODY_CODE_BY_NAME = {
    "Employment Appeals Tribunal": "2",
    "Equality Tribunal": "1",
    "Labour Court": "3",
    "Workplace Relations Commission": "15376",
}

BODY_FORM_FIELD_BY_NAME = {
    "Employment Appeals Tribunal": "ctl00$ContentPlaceHolder_Main$CB2$CB2_0",
    "Equality Tribunal": "ctl00$ContentPlaceHolder_Main$CB2$CB2_1",
    "Labour Court": "ctl00$ContentPlaceHolder_Main$CB2$CB2_2",
    "Workplace Relations Commission": "ctl00$ContentPlaceHolder_Main$CB2$CB2_3",
}


class WorkplaceRelationsQueryBuilder:
    base_url = "https://www.workplacerelations.ie/en/search/"

    def build_results_url(self, plan: SearchPlan, page_number: int = 1) -> str:
        params = {
            "advance": "true",
            "decisions": "1",
            "from": plan.partition.start_date.strftime("%d/%m/%Y"),
            "to": plan.partition.end_date.strftime("%d/%m/%Y"),
            "legislationsub": "",
            "pageNumber": str(page_number),
        }

        if plan.criteria.body:
            params["body"] = BODY_CODE_BY_NAME[plan.criteria.body]

        # These filters are intentionally centralized here so we can expand supported
        # query parameters without rewriting spider flow.
        if plan.criteria.topic:
            params["topic"] = plan.criteria.topic
        if plan.criteria.keyword:
            params["s"] = plan.criteria.keyword

        return f"{self.base_url}?{urlencode(params)}"

    def build_formdata(self, plan: SearchPlan) -> dict[str, str]:
        formdata = {
            "ctl00$ContentPlaceHolder_Main$TextBox2": plan.partition.start_date.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder_Main$TextBox3": plan.partition.end_date.strftime("%d/%m/%Y"),
            "ctl00$ContentPlaceHolder_Main$refine_btn": "",
        }

        if plan.criteria.body:
            formdata[BODY_FORM_FIELD_BY_NAME[plan.criteria.body]] = BODY_CODE_BY_NAME[plan.criteria.body]

        if plan.criteria.decision_number:
            formdata["ctl00$ContentPlaceHolder_Main$TextBox1"] = plan.criteria.decision_number
        if plan.criteria.case_number:
            formdata["ctl00$ContentPlaceHolder_Main$TextBox4"] = plan.criteria.case_number
        if plan.criteria.keyword:
            formdata["ctl00$ContentPlaceHolder_Main$TextBox5"] = plan.criteria.keyword
        if plan.criteria.topic:
            formdata["ctl00$ContentPlaceHolder_Main$DD4"] = plan.criteria.topic

        return formdata
