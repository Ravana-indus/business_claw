# -*- coding: utf-8 -*-
from frappe.model.document import Document
import frappe

class ChecklistRun(Document):
	def validate(self):
		# Auto-update status when all items are completed
		if self.items:
			all_completed = all(item.completed for item in self.items)
			if all_completed and self.status in ['Draft', 'In Progress']:
				self.status = 'In Progress'
				self.completed_date = frappe.utils.today()
	
	def on_submit(self):
		# Set status to Submitted on submit
		if self.status == 'Draft':
			self.status = 'In Progress'
	
	def on_cancel(self):
		# Reset status on cancel
		if self.status == 'Submitted':
			self.status = 'In Progress'
