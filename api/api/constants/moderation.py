from django.db import models


class DecisionAction(models.TextChoices):
    """
    This enumeration represents the actions that can be taken by a moderator as
    a part of a moderation decision.
    """

    MARKED_SENSITIVE = "marked_sensitive", "Marked sensitive"

    DEINDEXED_COPYRIGHT = "deindexed_copyright", "Deindexed (copyright)"
    DEINDEXED_SENSITIVE = "deindexed_sensitive", "Deindexed (sensitive)"

    REJECTED_REPORTS = "rejected_reports", "Rejected"
    DEDUPLICATED_REPORTS = "deduplicated_reports", "De-duplicated"

    REVERSED_MARK_SENSITIVE = "reversed_mark_sensitive", "Reversed mark sensitive"
    REVERSED_DEINDEX = "reversed_deindex", "Reversed deindex"

    @property
    def is_forward(self):
        return self in {
            self.MARKED_SENSITIVE,
            self.DEINDEXED_COPYRIGHT,
            self.DEINDEXED_SENSITIVE,
        }

    @property
    def is_reverse(self):
        return self in {self.REVERSED_DEINDEX, self.REVERSED_MARK_SENSITIVE}

    @property
    def is_deindex(self):
        return self in {self.DEINDEXED_COPYRIGHT, self.DEINDEXED_SENSITIVE}

    @property
    def verb(self) -> str:
        """
        Return the verb form of the action for use in sentences.

        :param object: the object of the sentence
        :return: the grammatically coherent verb phrase of the action
        """

        match self:
            case self.MARKED_SENSITIVE:
                return "marked as sensitive"
            case self.DEINDEXED_COPYRIGHT:
                return "deindexed (copyright)"
            case self.DEINDEXED_SENSITIVE:
                return "deindexed (sensitive)"
            case self.REJECTED_REPORTS:
                return "rejected"
            case self.DEDUPLICATED_REPORTS:
                return "de-duplicated"
            case self.REVERSED_MARK_SENSITIVE:
                return "unmarked as sensitive"
            case self.REVERSED_DEINDEX:
                return "reindexed"
