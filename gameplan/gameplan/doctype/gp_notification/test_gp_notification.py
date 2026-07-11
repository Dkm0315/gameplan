# Copyright (c) 2022, Frappe Technologies Pvt Ltd and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from gameplan.api import unread_notifications


class TestGPNotification(FrappeTestCase):
	def test_unread_notifications_counts_for_current_user(self):
		with patch.object(frappe.db, "count", return_value=3) as count:
			self.assertEqual(unread_notifications(), 3)

		count.assert_called_once_with(
			"GP Notification",
			filters={"to_user": frappe.session.user, "read": 0},
		)
