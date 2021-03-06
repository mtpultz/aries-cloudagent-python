"""Credential request message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_request import CredentialRequest
from ..messages.credential_proposal import CredentialProposal

from .....utils.tracing import trace_event, get_timer


class CredentialRequestHandler(BaseHandler):
    """Message handler class for credential requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential requests.

        Args:
            context: request context
            responder: responder callback

        """
        r_time = get_timer()

        self._logger.debug("CredentialRequestHandler called with context %s", context)
        assert isinstance(context.message, CredentialRequest)
        self._logger.info(
            "Received credential request message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential request")

        credential_manager = CredentialManager(context)
        cred_exchange_rec = await credential_manager.receive_request()

        r_time = trace_event(
            context.settings,
            context.message,
            outcome="CredentialRequestHandler.handle.END",
            perf_counter=r_time,
        )

        # If auto_issue is enabled, respond immediately
        if cred_exchange_rec.auto_issue:
            if (
                cred_exchange_rec.credential_proposal_dict
                and "credential_proposal" in cred_exchange_rec.credential_proposal_dict
            ):
                (
                    cred_exchange_rec,
                    credential_issue_message,
                ) = await credential_manager.issue_credential(
                    cred_ex_record=cred_exchange_rec,
                    comment=context.message.comment,
                    credential_values=CredentialProposal.deserialize(
                        cred_exchange_rec.credential_proposal_dict
                    ).credential_proposal.attr_dict(),
                )

                await responder.send_reply(credential_issue_message)

                trace_event(
                    context.settings,
                    credential_issue_message,
                    outcome="CredentialRequestHandler.issue.END",
                    perf_counter=r_time,
                )
            else:
                self._logger.warning(
                    "Operation set for auto-issue but credential exchange record "
                    f"{cred_exchange_rec.credential_exchange_id} "
                    "has no attribute values"
                )
