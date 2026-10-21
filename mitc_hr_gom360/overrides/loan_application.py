import frappe
from frappe.utils import flt
from lending.loan_management.doctype.loan_application.loan_application import LoanApplication

class CustomLoanApplication(LoanApplication):

    def validate(self):
        if self.repayment_method == "Repay Equal Principal":
            custom_period = getattr(self, "custom_rep_repayment_period_in_months", None)
            if custom_period:
                self.repayment_periods = custom_period
        
        super().validate()

    def get_repayment_details(self):
        if self.repayment_method == "Repay Equal Principal":
            periods = self.repayment_periods or getattr(self, "custom_rep_repayment_period_in_months", 0)
            
            if not periods:
                frappe.throw(frappe._("Repayment Period in Months is required for Equal Principal repayment."))

            self.repayment_periods = int(periods)
            loan_amount = flt(self.loan_amount)
            annual_rate = flt(self.rate_of_interest)
            
            # Estimate total interest for equal principal (Average balance method over time)
            # Total Interest approx = (Principal * Rate * (Periods + 1)) / (2400)
            total_interest = (loan_amount * annual_rate * (periods + 1)) / (24 * 100)
            total_payable = loan_amount + total_interest

            # Set fields expected by core Lending view
            self.total_payable_amount = flt(total_payable, self.precision("total_payable_amount"))
            self.total_payable_interest = flt(total_interest, self.precision("total_payable_interest"))
            self.repayment_amount = flt(loan_amount / periods + (loan_amount * annual_rate) / (12 * 100), self.precision("repayment_amount")) # First month payment as reference
            return

        super().get_repayment_details()
