<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "dashboardAdminUsers",
	components: {LocaleText},
	setup(){
		const store = DashboardConfigurationStore();
		return {store};
	},
	data(){
		return {
			admins: [],
			loading: true,
			showAddModal: false,
			showEditModal: false,
			showResetPasswordModal: false,
			showChangePasswordModal: false,
			// Add admin form
			newAdmin: {
				username: '',
				password: '',
				confirmPassword: '',
				email: ''
			},
			// Edit admin form
			editAdmin: {
				id: null,
				username: '',
				email: ''
			},
			// Reset password form
			resetPassword: {
				id: null,
				username: '',
				newPassword: '',
				confirmPassword: ''
			},
			// Change own password form
			changePassword: {
				currentPassword: '',
				newPassword: '',
				confirmPassword: ''
			},
			currentAdmin: null,
			saving: false
		}
	},
	mounted() {
		this.loadAdmins();
		this.loadCurrentAdmin();
	},
	methods: {
		async loadAdmins() {
			this.loading = true;
			await fetchGet("/api/admins", {}, (res) => {
				if(res.status){
					this.admins = res.data;
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
				this.loading = false;
			});
		},
		async loadCurrentAdmin() {
			await fetchGet("/api/admins/current", {}, (res) => {
				if(res.status){
					this.currentAdmin = res.data;
				}
			});
		},
		// Add Admin
		openAddModal() {
			this.newAdmin = { username: '', password: '', confirmPassword: '', email: '' };
			this.showAddModal = true;
		},
		async addAdmin() {
			if (!this.newAdmin.username || !this.newAdmin.password) {
				this.store.newMessage("Error", "Username and password are required", "danger");
				return;
			}
			if (this.newAdmin.password !== this.newAdmin.confirmPassword) {
				this.store.newMessage("Error", "Passwords do not match", "danger");
				return;
			}
			this.saving = true;
			await fetchPost("/api/admins/add", {
				username: this.newAdmin.username,
				password: this.newAdmin.password,
				email: this.newAdmin.email
			}, (res) => {
				if(res.status){
					this.store.newMessage("Server", "Admin created successfully", "success");
					this.showAddModal = false;
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
				this.saving = false;
			});
		},
		// Edit Admin
		openEditModal(admin) {
			this.editAdmin = {
				id: admin.id,
				username: admin.username,
				email: admin.email || ''
			};
			this.showEditModal = true;
		},
		async updateAdmin() {
			if (!this.editAdmin.username) {
				this.store.newMessage("Error", "Username is required", "danger");
				return;
			}
			this.saving = true;
			await fetchPost("/api/admins/update", {
				id: this.editAdmin.id,
				username: this.editAdmin.username,
				email: this.editAdmin.email
			}, (res) => {
				if(res.status){
					this.store.newMessage("Server", "Admin updated successfully", "success");
					this.showEditModal = false;
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
				this.saving = false;
			});
		},
		// Reset Password (for other admins)
		openResetPasswordModal(admin) {
			this.resetPassword = {
				id: admin.id,
				username: admin.username,
				newPassword: '',
				confirmPassword: ''
			};
			this.showResetPasswordModal = true;
		},
		async resetAdminPassword() {
			if (!this.resetPassword.newPassword) {
				this.store.newMessage("Error", "New password is required", "danger");
				return;
			}
			if (this.resetPassword.newPassword !== this.resetPassword.confirmPassword) {
				this.store.newMessage("Error", "Passwords do not match", "danger");
				return;
			}
			this.saving = true;
			await fetchPost("/api/admins/resetPassword", {
				id: this.resetPassword.id,
				newPassword: this.resetPassword.newPassword
			}, (res) => {
				if(res.status){
					this.store.newMessage("Server", "Password reset successfully", "success");
					this.showResetPasswordModal = false;
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
				this.saving = false;
			});
		},
		// Change Own Password
		openChangePasswordModal() {
			this.changePassword = {
				currentPassword: '',
				newPassword: '',
				confirmPassword: ''
			};
			this.showChangePasswordModal = true;
		},
		async changeOwnPassword() {
			if (!this.changePassword.currentPassword || !this.changePassword.newPassword) {
				this.store.newMessage("Error", "All fields are required", "danger");
				return;
			}
			if (this.changePassword.newPassword !== this.changePassword.confirmPassword) {
				this.store.newMessage("Error", "New passwords do not match", "danger");
				return;
			}
			this.saving = true;
			await fetchPost("/api/admins/changePassword", {
				currentPassword: this.changePassword.currentPassword,
				newPassword: this.changePassword.newPassword
			}, (res) => {
				if(res.status){
					this.store.newMessage("Server", "Password changed successfully", "success");
					this.showChangePasswordModal = false;
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
				this.saving = false;
			});
		},
		// Delete Admin
		async deleteAdmin(admin) {
			if (!confirm(`Are you sure you want to delete admin "${admin.username}"?`)) {
				return;
			}
			await fetchPost("/api/admins/delete", { id: admin.id }, (res) => {
				if(res.status){
					this.store.newMessage("Server", res.message, "success");
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		isCurrentAdmin(admin) {
			return this.currentAdmin && this.currentAdmin.id === admin.id;
		},
		formatDate(dateStr) {
			if (!dateStr) return 'Never';
			return new Date(dateStr).toLocaleString();
		}
	}
}
</script>

<template>
	<div class="card rounded-3">
		<div class="card-header d-flex align-items-center">
			<h6 class="my-2">
				<i class="bi bi-people-fill me-2"></i>
				<LocaleText t="Admin Users"></LocaleText>
			</h6>
			<span class="badge bg-primary ms-2">{{ admins.length }}</span>
		</div>
		<div class="card-body d-flex flex-column gap-2">
			<!-- Action buttons -->
			<div class="d-flex gap-2 mb-2">
				<button class="btn bg-primary-subtle text-primary-emphasis border-1 border-primary-subtle rounded-3 shadow-sm"
				        @click="openAddModal()">
					<i class="bi bi-person-plus-fill me-2"></i>
					<LocaleText t="Add Admin"></LocaleText>
				</button>
				<button class="btn bg-secondary-subtle text-secondary-emphasis border-1 border-secondary-subtle rounded-3 shadow-sm"
				        @click="openChangePasswordModal()">
					<i class="bi bi-key-fill me-2"></i>
					<LocaleText t="Change My Password"></LocaleText>
				</button>
			</div>
			
			<!-- Loading state -->
			<div v-if="loading" class="text-center py-4">
				<div class="spinner-border text-primary" role="status">
					<span class="visually-hidden">Loading...</span>
				</div>
			</div>
			
			<!-- Admin list -->
			<div v-else class="table-responsive">
				<table class="table table-hover mb-0">
					<thead>
						<tr>
							<th><LocaleText t="Username"></LocaleText></th>
							<th><LocaleText t="Email"></LocaleText></th>
							<th><LocaleText t="Created"></LocaleText></th>
							<th><LocaleText t="Last Login"></LocaleText></th>
							<th><LocaleText t="TOTP"></LocaleText></th>
							<th class="text-end"><LocaleText t="Actions"></LocaleText></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="admin in admins" :key="admin.id" 
						    :class="{'table-active': isCurrentAdmin(admin)}">
							<td>
								<i class="bi bi-person-fill me-1"></i>
								{{ admin.username }}
								<span v-if="isCurrentAdmin(admin)" class="badge bg-success ms-1">You</span>
							</td>
							<td>{{ admin.email || '-' }}</td>
							<td><small>{{ formatDate(admin.created_at) }}</small></td>
							<td><small>{{ formatDate(admin.last_login) }}</small></td>
							<td>
								<span v-if="admin.enable_totp" class="badge bg-success">
									<i class="bi bi-shield-check"></i> Enabled
								</span>
								<span v-else class="badge bg-secondary">Disabled</span>
							</td>
							<td class="text-end">
								<div class="btn-group btn-group-sm">
									<button class="btn btn-outline-primary" 
									        @click="openEditModal(admin)"
									        title="Edit">
										<i class="bi bi-pencil"></i>
									</button>
									<button class="btn btn-outline-warning" 
									        @click="openResetPasswordModal(admin)"
									        title="Reset Password">
										<i class="bi bi-key"></i>
									</button>
									<button class="btn btn-outline-danger" 
									        @click="deleteAdmin(admin)"
									        :disabled="isCurrentAdmin(admin) || admins.length <= 1"
									        title="Delete">
										<i class="bi bi-trash"></i>
									</button>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</div>
	
	<!-- Add Admin Modal -->
	<Teleport to="body">
		<div v-if="showAddModal" class="modal show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
			<div class="modal-dialog modal-dialog-centered">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">
							<i class="bi bi-person-plus-fill me-2"></i>Add New Admin
						</h5>
						<button type="button" class="btn-close" @click="showAddModal = false"></button>
					</div>
					<div class="modal-body">
						<div class="mb-3">
							<label class="form-label">Username <span class="text-danger">*</span></label>
							<input type="text" class="form-control" v-model="newAdmin.username" 
							       placeholder="Enter username" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Email</label>
							<input type="email" class="form-control" v-model="newAdmin.email" 
							       placeholder="Enter email (optional)" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="newAdmin.password" 
							       placeholder="Enter password" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Confirm Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="newAdmin.confirmPassword" 
							       placeholder="Confirm password" :disabled="saving">
						</div>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-secondary" @click="showAddModal = false" :disabled="saving">
							Cancel
						</button>
						<button type="button" class="btn btn-primary" @click="addAdmin()" :disabled="saving">
							<span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
							Add Admin
						</button>
					</div>
				</div>
			</div>
		</div>
	</Teleport>
	
	<!-- Edit Admin Modal -->
	<Teleport to="body">
		<div v-if="showEditModal" class="modal show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
			<div class="modal-dialog modal-dialog-centered">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">
							<i class="bi bi-pencil me-2"></i>Edit Admin
						</h5>
						<button type="button" class="btn-close" @click="showEditModal = false"></button>
					</div>
					<div class="modal-body">
						<div class="mb-3">
							<label class="form-label">Username <span class="text-danger">*</span></label>
							<input type="text" class="form-control" v-model="editAdmin.username" 
							       placeholder="Enter username" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Email</label>
							<input type="email" class="form-control" v-model="editAdmin.email" 
							       placeholder="Enter email (optional)" :disabled="saving">
						</div>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-secondary" @click="showEditModal = false" :disabled="saving">
							Cancel
						</button>
						<button type="button" class="btn btn-primary" @click="updateAdmin()" :disabled="saving">
							<span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
							Save Changes
						</button>
					</div>
				</div>
			</div>
		</div>
	</Teleport>
	
	<!-- Reset Password Modal -->
	<Teleport to="body">
		<div v-if="showResetPasswordModal" class="modal show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
			<div class="modal-dialog modal-dialog-centered">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">
							<i class="bi bi-key me-2"></i>Reset Password for {{ resetPassword.username }}
						</h5>
						<button type="button" class="btn-close" @click="showResetPasswordModal = false"></button>
					</div>
					<div class="modal-body">
						<div class="mb-3">
							<label class="form-label">New Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="resetPassword.newPassword" 
							       placeholder="Enter new password" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Confirm Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="resetPassword.confirmPassword" 
							       placeholder="Confirm new password" :disabled="saving">
						</div>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-secondary" @click="showResetPasswordModal = false" :disabled="saving">
							Cancel
						</button>
						<button type="button" class="btn btn-warning" @click="resetAdminPassword()" :disabled="saving">
							<span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
							Reset Password
						</button>
					</div>
				</div>
			</div>
		</div>
	</Teleport>
	
	<!-- Change Own Password Modal -->
	<Teleport to="body">
		<div v-if="showChangePasswordModal" class="modal show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
			<div class="modal-dialog modal-dialog-centered">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">
							<i class="bi bi-key-fill me-2"></i>Change Your Password
						</h5>
						<button type="button" class="btn-close" @click="showChangePasswordModal = false"></button>
					</div>
					<div class="modal-body">
						<div class="mb-3">
							<label class="form-label">Current Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="changePassword.currentPassword" 
							       placeholder="Enter current password" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">New Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="changePassword.newPassword" 
							       placeholder="Enter new password" :disabled="saving">
						</div>
						<div class="mb-3">
							<label class="form-label">Confirm New Password <span class="text-danger">*</span></label>
							<input type="password" class="form-control" v-model="changePassword.confirmPassword" 
							       placeholder="Confirm new password" :disabled="saving">
						</div>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-secondary" @click="showChangePasswordModal = false" :disabled="saving">
							Cancel
						</button>
						<button type="button" class="btn btn-primary" @click="changeOwnPassword()" :disabled="saving">
							<span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
							Change Password
						</button>
					</div>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<style scoped>
.table th {
	font-weight: 600;
	font-size: 0.85rem;
}
.table td {
	vertical-align: middle;
}
</style>
