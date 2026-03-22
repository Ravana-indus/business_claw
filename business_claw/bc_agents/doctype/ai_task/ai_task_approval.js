frappe.ui.form.on('AI Task', {
	refresh: function(frm) {
		if (frm.doc.status === 'Awaiting Approval') {
			frm.remove_custom_button('Save');
			frm.remove_custom_button('Delete');
			
			let approval_html = `
				<div class="row" style="margin-top: 20px;">
					<div class="col-md-12">
						<div class="alert alert-warning" style="text-align: center;">
							<h4>${__("Task Awaiting Approval")}</h4>
							<p>${__("This task has completed execution and is waiting for your approval.")}</p>
						</div>
					</div>
				</div>
				<div class="row" style="margin-top: 20px;">
					<div class="col-md-6" style="text-align: center;">
						<button class="btn btn-success btn-lg" id="approve-task-btn">
							<i class="fa fa-check"></i> ${__("Approve")}
						</button>
					</div>
					<div class="col-md-6" style="text-align: center;">
						<button class="btn btn-danger btn-lg" id="reject-task-btn">
							<i class="fa fa-times"></i> ${__("Reject")}
						</button>
					</div>
				</div>
			`;
			
			frm.dashboard_wrapper.html(approval_html);
			
			frm.on('approve-task-btn', function() {
				frappe.confirm(
					__('Are you sure you want to approve this task? This action will mark the task as completed.'),
					function() {
						frappe.call({
							method: 'business_claw.bc_agents.doctype.ai_task.ai_task.approve_task',
							args: {
								task_name: frm.doc.name
							},
							callback: function(r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.msgprint({
										message: __('Task approved successfully'),
										indicator: 'green'
									});
								}
							}
						});
					}
				);
			});
			
			frm.on('reject-task-btn', function() {
				frappe.prompt(
					[
						{
							fieldtype: 'Small Text',
							label: __('Reason for rejection'),
							fieldname: 'reason',
							reqd: 1,
							description: __('Please provide a reason for rejecting this task')
						}
					],
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
									frappe.msgprint({
										message: __('Task rejected'),
										indicator: 'orange'
									});
								}
							}
						});
					},
					__('Reject Task'),
					__('Reject')
				);
			});
		} else {
			frm.dashboard_wrapper.empty();
		}
	},
	
	status: function(frm) {
		frm.dirty();
		frm.refresh();
	}
});

frappe.ui.form.on('AI Task', {
	onload: function(frm) {
		if (frm.doc.status === 'Awaiting Approval') {
			frappe.call({
				method: 'business_claw.bc_agents.doctype.ai_task.ai_task.get_task_summary',
				args: {
					task_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message) {
						let summary = r.message;
						let summary_html = `
							<div class="form-dashboard">
								<div class="row">
									<div class="col-md-3">
										<div class="stat-widget">
											<div class="stat-label">${__("Tokens Consumed")}</div>
											<div class="stat-value">${summary.tokens_consumed || 0}</div>
										</div>
									</div>
									<div class="col-md-3">
										<div class="stat-widget">
											<div class="stat-label">${__("Execution Time")}</div>
											<div class="stat-value">${summary.execution_time || 0}s</div>
										</div>
									</div>
									<div class="col-md-3">
										<div class="stat-widget">
											<div class="stat-label">${__("Iterations")}</div>
											<div class="stat-value">${summary.iteration_count || 0}</div>
										</div>
									</div>
									<div class="col-md-3">
										<div class="stat-widget">
											<div class="stat-label">${__("Priority")}</div>
											<div class="stat-value">${summary.priority}</div>
										</div>
									</div>
								</div>
							</div>
						`;
						frm.dashboard.set_primary_action = function() {};
						$(summary_html).insertAfter(frm.fields_dict.status_section.$wrapper);
					}
				}
			});
		}
	}
});