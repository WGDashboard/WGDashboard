<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "dashboardAdmins",
	components: {LocaleText},
	setup() {
		const store = DashboardConfigurationStore();
		return {store};
	},
	data() {
		return {
			admins: [],
			loading: true,
			currentAdminID: null,
			showCreate: false,
			saving: false,
			createForm: {
				username: "",
				email: "",
				password: "",
				confirmPassword: ""
			},
			editAdmin: null,
			editForm: {
				AdminID: "",
				username: "",
				email: ""
			},
			passwordAdmin: null,
			passwordForm: {
				newPassword: "",
				confirmPassword: ""
			},
			pendingDelete: null
		}
	},
	mounted() {
		this.loadAdmins();
		fetchGet("/api/admins/me", {}, (res) => {
			if (res.status && res.data) {
				this.currentAdminID = res.data.AdminID;
			}
		})
	},
	computed: {
		enabledCount() {
			return this.admins.filter(x => x.Enabled === 1).length;
		}
	},
	methods: {
		loadAdmins() {
			fetchGet("/api/admins", {}, (res) => {
				this.loading = false;
				if (res.status) {
					this.admins = res.data;
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		resetMessages() {
			this.pendingDelete = null;
		},
		createAdmin() {
			if (this.createForm.password !== this.createForm.confirmPassword) {
				this.store.newMessage("Server", "Passwords do not match", "danger");
				return;
			}
			this.saving = true;
			fetchPost("/api/admins/add", this.createForm, (res) => {
				this.saving = false;
				if (res.status) {
					this.store.newMessage("Server", "Administrator created", "success");
					this.createForm = {username: "", email: "", password: "", confirmPassword: ""};
					this.showCreate = false;
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		startEdit(admin) {
			this.resetMessages();
			this.passwordAdmin = null;
			this.editAdmin = admin.AdminID;
			this.editForm = {
				AdminID: admin.AdminID,
				username: admin.Username,
				email: admin.Email
			};
		},
		saveEdit() {
			this.saving = true;
			fetchPost("/api/admins/update", this.editForm, (res) => {
				this.saving = false;
				if (res.status) {
					this.store.newMessage("Server", "Administrator updated", "success");
					this.editAdmin = null;
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		startPassword(admin) {
			this.resetMessages();
			this.editAdmin = null;
			this.passwordAdmin = admin.AdminID;
			this.passwordForm = {newPassword: "", confirmPassword: ""};
		},
		savePassword() {
			if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
				this.store.newMessage("Server", "Passwords do not match", "danger");
				return;
			}
			this.saving = true;
			fetchPost("/api/admins/setPassword", {
				AdminID: this.passwordAdmin,
				newPassword: this.passwordForm.newPassword,
				confirmPassword: this.passwordForm.confirmPassword
			}, (res) => {
				this.saving = false;
				if (res.status) {
					this.store.newMessage("Server", "Password updated", "success");
					this.passwordAdmin = null;
					this.passwordForm = {newPassword: "", confirmPassword: ""};
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		toggleAdmin(admin) {
			this.resetMessages();
			fetchPost("/api/admins/toggle", {
				AdminID: admin.AdminID,
				Enabled: admin.Enabled !== 1
			}, (res) => {
				if (res.status) {
					this.store.newMessage("Server", admin.Enabled === 1 ? "Administrator disabled" : "Administrator enabled", "success");
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		deleteAdmin(admin) {
			if (this.pendingDelete !== admin.AdminID) {
				this.pendingDelete = admin.AdminID;
				return;
			}
			fetchPost("/api/admins/delete", {AdminID: admin.AdminID}, (res) => {
				this.pendingDelete = null;
				if (res.status) {
					this.store.newMessage("Server", "Administrator deleted", "success");
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		}
	}
}
</script>

<template>
	<div class="d-flex flex-column gap-3">
		<div class="card rounded-3 shadow-sm" v-if="this.showCreate">
			<div class="card-header d-flex align-items-center">
				<h6 class="my-2">
					<i class="bi bi-person-plus-fill me-2"></i>
					<LocaleText t="Add administrator"></LocaleText>
				</h6>
				<button type="button" class="btn-close ms-auto" @click="this.showCreate = false"></button>
			</div>
			<div class="card-body d-flex flex-column gap-3">
				<div class="row gy-2">
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Username"></LocaleText></small></label>
						<input class="form-control form-control-sm rounded-3" autocomplete="off" v-model="this.createForm.username">
					</div>
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Email"></LocaleText></small></label>
						<input class="form-control form-control-sm rounded-3" autocomplete="off" v-model="this.createForm.email">
					</div>
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Password"></LocaleText></small></label>
						<input type="password" class="form-control form-control-sm rounded-3" autocomplete="new-password" v-model="this.createForm.password">
					</div>
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Confirm password"></LocaleText></small></label>
						<input type="password" class="form-control form-control-sm rounded-3" autocomplete="new-password" v-model="this.createForm.confirmPassword">
					</div>
				</div>
				<small class="text-muted">
					<i class="bi bi-info-circle me-1"></i>
					<LocaleText t="At least 8 characters, with 1 lowercase, 1 uppercase, 1 number and 1 special character"></LocaleText>
				</small>
				<div class="d-flex gap-2 justify-content-end">
					<button class="btn btn-secondary btn-sm rounded-3 px-3" @click="this.showCreate = false">
						<LocaleText t="Cancel"></LocaleText>
					</button>
					<button class="btn btn-primary btn-sm rounded-3 px-3" :disabled="this.saving" @click="this.createAdmin()">
						<i class="bi bi-plus-circle-fill me-1"></i><LocaleText t="Add"></LocaleText>
					</button>
				</div>
			</div>
		</div>

		<div class="card rounded-3 shadow-sm" v-if="this.editAdmin !== null">
			<div class="card-header d-flex align-items-center">
				<h6 class="my-2"><i class="bi bi-pencil-square me-2"></i><LocaleText t="Edit administrator"></LocaleText></h6>
				<button type="button" class="btn-close ms-auto" @click="this.editAdmin = null"></button>
			</div>
			<div class="card-body d-flex flex-column gap-3">
				<div class="row gy-2">
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Username"></LocaleText></small></label>
						<input class="form-control form-control-sm rounded-3" autocomplete="off" v-model="this.editForm.username">
					</div>
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Email"></LocaleText></small></label>
						<input class="form-control form-control-sm rounded-3" autocomplete="off" v-model="this.editForm.email">
					</div>
				</div>
				<div class="d-flex gap-2 justify-content-end">
					<button class="btn btn-secondary btn-sm rounded-3 px-3" @click="this.editAdmin = null">
						<LocaleText t="Cancel"></LocaleText>
					</button>
					<button class="btn btn-primary btn-sm rounded-3 px-3" :disabled="this.saving" @click="this.saveEdit()">
						<i class="bi bi-check-lg me-1"></i><LocaleText t="Save"></LocaleText>
					</button>
				</div>
			</div>
		</div>

		<div class="card rounded-3 shadow-sm" v-if="this.passwordAdmin !== null">
			<div class="card-header d-flex align-items-center">
				<h6 class="my-2"><i class="bi bi-key-fill me-2"></i><LocaleText t="Change password"></LocaleText></h6>
				<button type="button" class="btn-close ms-auto" @click="this.passwordAdmin = null"></button>
			</div>
			<div class="card-body d-flex flex-column gap-3">
				<div class="row gy-2">
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="New Password"></LocaleText></small></label>
						<input type="password" class="form-control form-control-sm rounded-3" autocomplete="new-password" v-model="this.passwordForm.newPassword">
					</div>
					<div class="col-md-6">
						<label class="form-label mb-1"><small class="text-muted"><LocaleText t="Confirm password"></LocaleText></small></label>
						<input type="password" class="form-control form-control-sm rounded-3" autocomplete="new-password" v-model="this.passwordForm.confirmPassword">
					</div>
				</div>
				<div class="d-flex gap-2 justify-content-end">
					<button class="btn btn-secondary btn-sm rounded-3 px-3" @click="this.passwordAdmin = null">
						<LocaleText t="Cancel"></LocaleText>
					</button>
					<button class="btn btn-primary btn-sm rounded-3 px-3" :disabled="this.saving" @click="this.savePassword()">
						<i class="bi bi-check-lg me-1"></i><LocaleText t="Save"></LocaleText>
					</button>
				</div>
			</div>
		</div>


		<div class="card rounded-3">
			<div class="card-header d-flex align-items-center">
				<h6 class="my-2">
					<i class="bi bi-people-fill me-2"></i>
					<LocaleText t="Administrators"></LocaleText>
					<span class="badge text-bg-secondary ms-2">{{ this.admins.length }}</span>
				</h6>
				<button class="btn btn-sm btn-primary rounded-3 px-3 ms-auto" v-if="!this.showCreate"
				        @click="this.showCreate = true; this.editAdmin = null; this.passwordAdmin = null">
					<i class="bi bi-plus-circle-fill me-1"></i><LocaleText t="Add administrator"></LocaleText>
				</button>
			</div>
			<div class="card-body">
				<div class="text-muted text-center py-4" v-if="this.loading">
					<div class="spinner-border spinner-border-sm me-2"></div><LocaleText t="Loading..."></LocaleText>
				</div>
				<div class="table-responsive" v-else>
					<table class="table table-sm align-middle mb-0">
						<thead>
						<tr>
							<th><small class="text-muted"><LocaleText t="Username"></LocaleText></small></th>
							<th><small class="text-muted"><LocaleText t="Email"></LocaleText></small></th>
							<th><small class="text-muted"><LocaleText t="Status"></LocaleText></small></th>
							<th><small class="text-muted"><LocaleText t="Last login"></LocaleText></small></th>
							<th class="text-end"><small class="text-muted"><LocaleText t="Actions"></LocaleText></small></th>
						</tr>
						</thead>
						<tbody>
						<tr v-for="admin in this.admins" :key="admin.AdminID">
							<td>
								<span class="fw-bold">{{ admin.Username }}</span>
								<span class="badge text-bg-info ms-2" v-if="admin.AdminID === this.currentAdminID">
									<LocaleText t="Current session"></LocaleText>
								</span>
								<i class="bi bi-shield-lock-fill ms-2 text-success" v-if="admin.TotpEnabled" title="TOTP"></i>
							</td>
							<td><span class="text-muted">{{ admin.Email || "-" }}</span></td>
							<td>
								<span class="badge" :class="admin.Enabled === 1 ? 'text-bg-success' : 'text-bg-secondary'">
									<LocaleText :t="admin.Enabled === 1 ? 'Enabled' : 'Disabled'"></LocaleText>
								</span>
							</td>
							<td><small class="text-muted">{{ admin.LastLoginDate || "-" }}</small></td>
							<td class="text-end">
								<div class="btn-group btn-group-sm">
									<button class="btn btn-outline-secondary rounded-start-3" title="Edit" @click="this.startEdit(admin)">
										<i class="bi bi-pencil-square"></i>
									</button>
									<button class="btn btn-outline-secondary" title="Change password" @click="this.startPassword(admin)">
										<i class="bi bi-key-fill"></i>
									</button>
									<button class="btn btn-outline-secondary" :title="admin.Enabled === 1 ? 'Disable' : 'Enable'" @click="this.toggleAdmin(admin)">
										<i class="bi" :class="admin.Enabled === 1 ? 'bi-pause-fill' : 'bi-play-fill'"></i>
									</button>
									<button class="btn rounded-end-3"
									        :class="this.pendingDelete === admin.AdminID ? 'btn-danger' : 'btn-outline-danger'"
									        :disabled="admin.AdminID === this.currentAdminID"
									        title="Delete"
									        @click="this.deleteAdmin(admin)">
										<i class="bi bi-trash-fill" v-if="this.pendingDelete !== admin.AdminID"></i>
										<small v-else><LocaleText t="Confirm"></LocaleText></small>
									</button>
								</div>
							</td>
						</tr>
						<tr v-if="this.admins.length === 0">
							<td colspan="5" class="text-center text-muted py-4">
								<LocaleText t="No administrator"></LocaleText>
							</td>
						</tr>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.btn-group .btn {
	border-radius: 0;
}
</style>

