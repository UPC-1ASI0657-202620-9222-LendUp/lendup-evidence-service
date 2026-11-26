from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.application.services import incident_closure as closure


@pytest.mark.parametrize("generation", [None, str(uuid4())])
def test_reconciles_current_seal_after_confirmed_rollback(monkeypatch, generation):
    session = Mock()
    loan = uuid4()
    observed = closure.ReportAdmission(True, generation)

    def check_loan(id):
        session.rollback.assert_called_once()
        assert id == loan
        return True

    monkeypatch.setattr(closure, "loan_accepts_reports", check_loan)
    monkeypatch.setattr(closure, "lock_report_admission", lambda *_: observed)
    closure.reconcile_report_admission(session, loan, observed)
    statement = session.execute.call_args.args[0]
    assert statement.table.name == "cierres_incidencias"
    assert statement.compile().params["sellado"] is False
    session.commit.assert_not_called()


def test_does_not_remove_seal_from_a_newer_close(monkeypatch):
    session = Mock()
    monkeypatch.setattr(closure, "loan_accepts_reports", lambda _: True)
    monkeypatch.setattr(closure, "lock_report_admission", lambda *_: closure.ReportAdmission(True, str(uuid4())))
    with pytest.raises(HTTPException) as error:
        closure.reconcile_report_admission(session, uuid4(), closure.ReportAdmission(True, str(uuid4())))
    assert error.value.status_code == 409
    session.execute.assert_not_called()


def test_committed_close_and_unknown_outcome_keep_the_seal(monkeypatch):
    session = Mock()
    observed = closure.ReportAdmission(True, str(uuid4()))
    monkeypatch.setattr(closure, "loan_accepts_reports", lambda _: False)
    with pytest.raises(HTTPException) as closed:
        closure.reconcile_report_admission(session, uuid4(), observed)
    assert closed.value.status_code == 409

    def unavailable(_):
        raise HTTPException(503)

    monkeypatch.setattr(closure, "loan_accepts_reports", unavailable)
    with pytest.raises(HTTPException) as failed:
        closure.reconcile_report_admission(session, uuid4(), observed)
    assert failed.value.status_code == 503
    session.execute.assert_not_called()
