frappe.listview_settings['AI Task'] = {
	add_fields: ['title', 'status', 'priority', 'assigned_agent', 'parent_task', 'due_date', 'iteration_count', 'creation'],
	get_indicator: function(doc) {
		const colors = {
			'Pending': 'orange',
			'Processing': 'blue',
			'Awaiting Approval': 'purple',
			'Delegated': 'cyan',
			'Completed': 'green',
			'Failed': 'red',
			'Cancelled': 'grey'
		};
		
		const priority_colors = {
			'Critical': 'red',
			'High': 'orange',
			'Medium': 'blue',
			'Low': 'grey'
		};
		
		let color = colors[doc.status] || 'grey';
		
		if (doc.status === 'Pending' && doc.priority === 'Critical') {
			color = 'red';
		} else if (doc.status === 'Pending' && doc.priority === 'High') {
			color = 'orange';
		}
		
		return [__(doc.status), color, 'status,=,' + doc.status];
	},
	button: {
		show: function(doc) {
			return true;
		},
		get_label: function() {
			return __('View');
		},
		action: function(doc) {
			frappe.set_route('Form', 'AI Task', doc.name);
		}
	},
	onload: function(listview) {
		listview.page.add_menu_item(__('Mark as Processing'), function() {
			const docname = listview.get_checked_items();
			if (docname.length === 0) {
				frappe.msgprint(__('Please select at least one task'));
				return;
			}
			frappe.call({
				method: 'business_claw.bc_agents.doctype.ai_task.ai_task.bulk_update_status',
				args: {
					task_names: docname,
					status: 'Processing'
				},
				callback: function(r) {
					if (!r.exc) {
						listview.refresh();
						frappe.msgprint(__('Tasks marked as Processing'));
					}
				}
			});
		});
		
		listview.page.add_menu_item(__('Mark as Completed'), function() {
			const docname = listview.get_checked_items();
			if (docname.length === 0) {
				frappe.msgprint(__('Please select at least one task'));
				return;
			}
			frappe.call({
				method: 'business_claw.bc_agents.doctype.ai_task.ai_task.bulk_update_status',
				args: {
					task_names: docname,
					status: 'Completed'
				},
				callback: function(r) {
					if (!r.exc) {
						listview.refresh();
						frappe.msgprint(__('Tasks marked as Completed'));
					}
				}
			});
		});
	}
};

frappe.ui.form.on('AI Task', {
	refresh: function(frm) {
		if (frm.doc.status === 'Awaiting Approval') {
			frm.add_custom_button(__('Approve'), function() {
				frappe.confirm(
					__('Are you sure you want to approve this task?'),
					function() {
						frappe.call({
							method: 'business_claw.bc_agents.doctype.ai_task.ai_task.approve_task',
							args: {
								task_name: frm.doc.name
							},
							callback: function(r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.msgprint(__('Task approved successfully'));
								}
							}
						});
					}
				);
			}, __('Actions'));
			
			frm.add_custom_button(__('Reject'), function() {
				frappe.prompt(
					{
						fieldtype: 'Small Text',
						label: __('Reason for rejection'),
						fieldname: 'reason',
						reqd: 1
					},
				 function(values) {
						frappe.call({
							method: 'business_claw.bc_agents.doctype.ai_task.ai_task.reject_task',
							args: {
								task_name: frm.doc.name,
								reason: values.reason
							},
							callback: function(r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.msgprint(__('Task rejected'));
								}
							}
						});
					},
					__('Reject Task'),
					__('Reject')
				);
			}, __('Actions'));
		}
		
		frm.add_custom_button(__('Create Child Task'), function() {
			frappe.new_doc('AI Task', {
				parent_task: frm.doc.name,
				priority: frm.doc.priority,
				due_date: frm.doc.due_date
			});
		}, __('Actions'));
		
		if (frm.doc.status === 'Pending' || frm.doc.status === 'Delegated') {
			frm.add_custom_button(__('Start Processing'), function() {
				frappe.call({
					method: 'business_claw.bc_agents.doctype.ai_task.ai_task.start_task',
					args: {
						task_name: frm.doc.name
					},
					callback: function(r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.msgprint(__('Task started'));
						}
					}
				});
			}, __('Actions'));
		}
		
		if (frm.doc.child_tasks && frm.doc.child_tasks.length > 0) {
			frm.add_custom_button(__('View Child Tasks'), function() {
				frappe.route_options = {
					parent_task: frm.doc.name
				};
				frappe.set_route('List', 'AI Task');
			}, __('Actions'));
		}
	},
	
	assigned_agent: function(frm) {
		if (frm.doc.assigned_agent) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'AI Agent',
					name: frm.doc.assigned_agent
				},
				callback: function(r) {
					if (r.message && !r.message.is_active) {
						frappe.msgprint({
							title: __('Warning'),
							message: __('The selected agent is not active'),
							indicator: 'orange'
						});
					}
				}
			});
		}
	},
	
	input_payload: function(frm) {
		if (frm.doc.input_payload) {
			try {
				JSON.parse(frm.doc.input_payload);
				frm.set_value('input_payload', JSON.stringify(JSON.parse(frm.doc.input_payload), null, 2));
			} catch (e) {
				frappe.msgprint({
					title: __('Invalid JSON'),
					message: __('Input payload must be valid JSON'),
					indicator: 'red'
				});
			}
		}
	}
});