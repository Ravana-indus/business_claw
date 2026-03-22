frappe.ui.form.on('AI Agent', {
	refresh: function(frm) {
		frm.add_custom_button(__('Create Task'), function() {
			frappe.new_doc('AI Task', {
				assigned_agent: frm.doc.name
			});
		}, __('Actions'));
		
		frm.add_custom_button(__('Test Connection'), function() {
			frappe.call({
				method: 'business_claw.bc_agents.api.test_agent_connection',
				args: { agent: frm.doc.name },
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(__('Agent connection successful'));
					} else {
						frappe.msgprint({
							title: __('Error'),
							message: r.message && r.message.error || __('Connection test failed'),
							indicator: 'red'
						});
					}
				}
			});
		}, __('Actions'));
		
		frm.add_custom_button(__('View Capabilities'), function() {
			if (frm.doc.capabilities && frm.doc.capabilities.length > 0) {
				let html = '<table class="table table-bordered"><tr><th>Capability</th><th>Description</th></tr>';
				frm.doc.capabilities.forEach(function(cap) {
					html += `<tr><td>${cap.capability}</td><td>${cap.description || ''}</td></tr>`;
				});
				html += '</table>';
				frappe.msgprint(html, __('Agent Capabilities'));
			} else {
				frappe.msgprint(__('No capabilities defined'), __('Agent Capabilities'));
			}
		}, __('Actions'));
	},
	
	is_active: function(frm) {
		if (!frm.doc.is_active && frm.doc.status !== 'Offline') {
			frm.set_value('status', 'Offline');
		}
	},
	
	agent_role: function(frm) {
		if (frm.doc.agent_role && !frm.doc.system_prompt) {
			frm.trigger('set_default_prompt');
		}
	},
	
	agent_type: function(frm) {
		if (frm.doc.agent_role && !frm.doc.system_prompt) {
			frm.trigger('set_default_prompt');
		}
	}
});

frappe.listview_settings['AI Agent'] = {
	add_fields: ['agent_name', 'agent_role', 'agent_type', 'status', 'is_active', 'last_active'],
	get_indicator: function(doc) {
		if (!doc.is_active) {
			return [__('Inactive'), 'red', 'is_active,=,' + (doc.is_active ? '1' : '0')];
		}
		if (doc.status === 'Working') {
			return [__('Working'), 'blue', 'status,=,' + doc.status];
		}
		if (doc.status === 'Error') {
			return [__('Error'), 'red', 'status,=,' + doc.status];
		}
		return [__('Idle'), 'green', 'status,=,' + doc.status];
	},
	button: {
		show: function(doc) {
			return doc.is_active;
		}
	}
};
