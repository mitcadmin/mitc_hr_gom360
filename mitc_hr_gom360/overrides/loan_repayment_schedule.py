import frappe
from frappe import _
from frappe.utils import flt, cint

from lending.loan_management.doctype.loan_repayment_schedule.loan_repayment_schedule import (
    LoanRepaymentSchedule as BaseLoanRepaymentSchedule,
)


class LoanRepaymentSchedule(BaseLoanRepaymentSchedule):
    """
    Custom Loan Repayment Schedule controller.

    Adds support for:

        Repay Equal Principal

    Behaviour:
        - Principal is divided equally across the repayment periods.
        - Interest is calculated on the outstanding principal.
        - Therefore interest decreases every month.
        - Therefore total repayment decreases every month.
        - The final principal installment absorbs rounding differences.
    """

    def make_customer_repayment_schedule(self):
        """
        Let standard Lending generate the schedule first.

        For all existing repayment methods, behaviour remains unchanged.

        For 'Repay Equal Principal', we then replace the generated
        principal/interest/total amounts with an equal-principal schedule.
        """

        # ------------------------------------------------------------
        # STANDARD LENDING BEHAVIOUR
        # ------------------------------------------------------------
        super().make_customer_repayment_schedule()

        # ------------------------------------------------------------
        # CUSTOM METHOD
        # ------------------------------------------------------------
        if self.repayment_method != "Repay Equal Principal":
            return

        self.make_equal_principal_schedule()

    def make_equal_principal_schedule(self):
        """
        Convert the generated repayment schedule into an
        equal-principal / declining-interest schedule.
        """

        if self.repayment_frequency != "Monthly":
            frappe.throw(
                _(
                    "Repay Equal Principal currently supports Monthly "
                    "repayment frequency only."
                )
            )

        if not self.repayment_periods:
            frappe.throw(
                _("Repayment Periods must be greater than zero.")
            )

        if not self.current_principal_amount:
            frappe.throw(
                _("Current Principal Amount must be greater than zero.")
            )

        schedule = self.get("repayment_schedule")

        if not schedule:
            frappe.throw(
                _("No repayment schedule rows were generated.")
            )

        precision = cint(frappe.db.get_default("currency_precision")) or 2

        # ------------------------------------------------------------
        # PRINCIPAL
        # ------------------------------------------------------------
        #
        # Example:
        #
        # Loan = 1,848,753.62
        # Periods = 23
        #
        # 1,848,753.62 / 23
        # = 80,380.59217...
        #
        # Rounded monthly principal:
        # = 80,380.59
        #
        # The final installment receives the remaining balance:
        # = 80,380.64
        #
        original_principal = flt(self.current_principal_amount)

        equal_principal = flt(
            original_principal / self.repayment_periods,
            precision,
        )

        balance = original_principal

        principal_rows = [
            row
            for row in schedule
            if flt(row.principal_amount) > 0
        ]

        # ------------------------------------------------------------
        # SAFETY CHECK
        # ------------------------------------------------------------
        #
        # For a normal equal-principal loan we expect one
        # principal-bearing row per repayment period.
        #
        if len(principal_rows) != self.repayment_periods:
            frappe.throw(
                _(
                    "Equal Principal schedule expected {0} "
                    "principal repayment rows, but found {1}. "
                    "Please check the loan configuration."
                ).format(
                    self.repayment_periods,
                    len(principal_rows),
                )
            )

        # ------------------------------------------------------------
        # GENERATE EQUAL-PRINCIPAL SCHEDULE
        # ------------------------------------------------------------

        for index, row in enumerate(principal_rows, start=1):

            # --------------------------------------------------------
            # Principal
            # --------------------------------------------------------
            #
            # Every installment receives the same principal except
            # the final installment, which clears the exact remaining
            # balance after rounding.
            #
            if index < self.repayment_periods:
                principal_amount = equal_principal
            else:
                principal_amount = flt(balance, precision)

            # --------------------------------------------------------
            # Interest
            # --------------------------------------------------------
            #
            # Monthly reducing-balance interest:
            #
            # outstanding principal × annual rate / 12
            #
            interest_amount = flt(
                balance
                * flt(self.rate_of_interest)
                / 12
                / 100,
                precision,
            )

            # --------------------------------------------------------
            # Total repayment
            # --------------------------------------------------------
            total_payment = flt(
                principal_amount + interest_amount,
                precision,
            )

            # --------------------------------------------------------
            # Remaining balance
            # --------------------------------------------------------
            balance = flt(
                balance - principal_amount,
                precision,
            )

            if balance < 0:
                balance = 0

            # --------------------------------------------------------
            # Update existing repayment row
            # --------------------------------------------------------
            row.principal_amount = principal_amount
            row.interest_amount = interest_amount
            row.total_payment = total_payment
            row.balance_loan_amount = balance

        # ------------------------------------------------------------
        # FINAL ROUNDING CORRECTION
        # ------------------------------------------------------------
        #
        # Ensure the loan ends exactly at zero.
        #
        if principal_rows:
            final_row = principal_rows[-1]

            final_row.principal_amount = flt(
                final_row.principal_amount + balance,
                precision,
            )

            final_row.total_payment = flt(
                final_row.principal_amount
                + final_row.interest_amount,
                precision,
            )

            final_row.balance_loan_amount = 0

        # ------------------------------------------------------------
        # monthly_repayment_amount
        # ------------------------------------------------------------
        #
        # Lending has this field because the standard system expects
        # a single monthly repayment amount.
        #
        # Equal Principal does not have one fixed monthly amount.
        #
        # We therefore store the FIRST installment as the
        # representative amount rather than setting it to zero.
        #
        if principal_rows:
            self.monthly_repayment_amount = flt(
                principal_rows[0].total_payment,
                precision,
            )
