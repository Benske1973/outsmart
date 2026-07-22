class WorkorderComparator:
    def compare(self, mail_data, workorder):
        result = {
            "matches": [],
            "differences": [],
            "missing_in_workorder": [],
            "missing_in_mail": [],
        }
        for field in ["order", "purchase_order", "customer", "address"]:
            mail_value = mail_data.get(field)
            workorder_value = workorder.get(field)
            if mail_value and workorder_value and str(mail_value) == str(workorder_value):
                result["matches"].append(field)
            elif mail_value or workorder_value:
                result["differences"].append({
                    "field": field,
                    "mail": mail_value,
                    "workorder": workorder_value,
                })
        return result
