<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";
import QRCode from "qrcode";

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
			pendingDelete: null,
			mfaAdminID: null,
			mfaLink: "",
			mfaSecret: "",
			mfaCode: "",
			mfaPassword: "",
			mfaBusy: false,
			recoveryCodes: []
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
		},
		mfaTarget() {
			return this.admins.find(x => x.AdminID === this.mfaAdminID) || null;
		},
		mfaIsOwnAccount() {
			return this.mfaAdminID !== null && this.mfaAdminID === this.currentAdminID;
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
		},
		openMfa(admin) {
			this.resetMessages();
			this.editAdmin = null;
			this.passwordAdmin = null;
			this.mfaAdminID = admin.AdminID;
			this.mfaLink = "";
			this.mfaSecret = "";
			this.mfaCode = "";
			this.mfaPassword = "";
			this.recoveryCodes = [];
			if (admin.TotpEnabled !== true) {
				this.startMfa();
			}
		},
		closeMfa() {
			this.mfaAdminID = null;
			this.mfaLink = "";
			this.mfaSecret = "";
			this.mfaCode = "";
			this.mfaPassword = "";
			this.mfaBusy = false;
			this.recoveryCodes = [];
		},
		startMfa() {
			this.mfaBusy = true;
			fetchPost("/api/admins/totp/start", {AdminID: this.mfaAdminID}, (res) => {
				this.mfaBusy = false;
				if (res.status && res.data) {
					this.mfaLink = res.data.Link;
					this.mfaSecret = res.data.Secret;
					this.$nextTick(() => {
						const canvas = document.getElementById("mfa_qrcode");
						if (canvas) {
							QRCode.toCanvas(canvas, this.mfaLink, {width: 220, margin: 1}, () => {
							});
						}
					});
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		verifyMfa() {
			if (!/^[0-9]{6}$/.test(this.mfaCode)) {
				this.store.newMessage("Server", "The code must contain 6 digits", "danger");
				return;
			}
			this.mfaBusy = true;
			fetchPost("/api/admins/totp/verify", {AdminID: this.mfaAdminID, code: this.mfaCode}, (res) => {
				this.mfaBusy = false;
				if (res.status) {
					this.store.newMessage("Server", "MFA enabled for this administrator", "success");
					this.closeMfa();
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		disableMfa() {
			if (this.mfaIsOwnAccount && this.mfaPassword.length === 0) {
				this.store.newMessage("Server", "Please enter your current password", "danger");
				return;
			}
			this.mfaBusy = true;
			fetchPost("/api/admins/totp/disable", {
				AdminID: this.mfaAdminID,
				currentPassword: this.mfaPassword
			}, (res) => {
				this.mfaBusy = false;
				if (res.status) {
					this.store.newMessage("Server", "MFA disabled for this administrator", "success");
					this.closeMfa();
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		generateRecoveryCodes() {
			this.mfaBusy = true;
			fetchPost("/api/admins/totp/recoveryCodes", {
				AdminID: this.mfaAdminID,
				currentPassword: this.mfaPassword
			}, (res) => {
				this.mfaBusy = false;
				if (res.status && res.data) {
					this.recoveryCodes = res.data.Codes || [];
					this.store.newMessage("Server", "New recovery codes generated: save them now", "success");
					this.loadAdmins();
				} else {
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		revokeRecoveryCodes() {
			this.mfaBusy = true;
			fetchPost("/api/admins/totp/recoveryCodes/revoke", {
				AdminID: this.mfaAdminID,
				currentPassword: this.mfaPassword
			}, (res) => {
				this.mfaBusy = false;
				if (res.status) {
					this.recoveryCodes = [];
					this.store.newMessage("Server", "Recovery codes revoked", "success");
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


		<div class="card rounded-3 shadow-sm" v-if="this.mfaAdminID !== null">
			<div class="card-header d-flex align-items-center">
				<h6 class="my-2">
					<i class="bi bi-shield-lock-fill me-2"></i>
					<LocaleText t="Multi-Factor Authentication (MFA)"></LocaleText>
					<code class="ms-2" v-if="this.mfaTarget">{{ this.mfaTarget.Username }}</code>
				</h6>
				<button type="button" class="btn-close ms-auto" @click="this.closeMfa()"></button>
			</div>
			<div class="card-body d-flex flex-column gap-3">
				<template v-if="this.mfaTarget && this.mfaTarget.TotpEnabled">
					<div class="alert alert-success py-2 mb-0">
						<small>
							<i class="bi bi-shield-check me-1"></i>
							<LocaleText t="MFA is enabled for this administrator"></LocaleText>
						</small>
					</div>
					<div v-if="this.mfaIsOwnAccount">
						<label class="form-label mb-1">
							<small class="text-muted"><LocaleText t="Current Password"></LocaleText></small>
						</label>
						<input type="password" class="form-control form-control-sm rounded-3"
						       autocomplete="current-password" v-model="this.mfaPassword">
					</div>
					<div class="d-flex gap-2 justify-content-end">
						<button class="btn btn-secondary btn-sm rounded-3 px-3" @click="this.closeMfa()">
							<LocaleText t="Cancel"></LocaleText>
						</button>
						<button class="btn btn-danger btn-sm rounded-3 px-3" :disabled="this.mfaBusy" @click="this.disableMfa()">
							<i class="bi bi-shield-slash-fill me-1"></i><LocaleText t="Disable MFA"></LocaleText>
						</button>
					</div>
					<hr class="my-1">
					<div class="d-flex align-items-center gap-2 flex-wrap">
						<small class="text-muted">
							<i class="bi bi-life-preserver me-1"></i>
							<LocaleText t="Recovery codes"></LocaleText> :
							<strong>{{ this.mfaTarget ? this.mfaTarget.RecoveryCodesRemaining : 0 }}</strong>
							<LocaleText t="remaining"></LocaleText>
						</small>
						<div class="ms-auto d-flex gap-2">
							<button class="btn btn-outline-secondary btn-sm rounded-3 px-3" :disabled="this.mfaBusy"
							        @click="this.generateRecoveryCodes()">
								<i class="bi bi-arrow-repeat me-1"></i>
								<LocaleText :t="this.mfaTarget && this.mfaTarget.RecoveryCodesRemaining > 0 ? 'Regenerate' : 'Generate'"></LocaleText>
							</button>
							<button class="btn btn-outline-danger btn-sm rounded-3 px-3" :disabled="this.mfaBusy"
							        v-if="this.mfaTarget && this.mfaTarget.RecoveryCodesRemaining > 0"
							        @click="this.revokeRecoveryCodes()">
								<i class="bi bi-x-circle me-1"></i><LocaleText t="Revoke"></LocaleText>
							</button>
						</div>
					</div>
					<div class="p-3 bg-body-secondary rounded-3 border" v-if="this.recoveryCodes.length > 0">
						<small class="text-muted d-block mb-2">
							<LocaleText t="Save these codes now: they will not be shown again."></LocaleText>
						</small>
						<div class="row row-cols-2 g-2">
							<div class="col" v-for="code in this.recoveryCodes" :key="code">
								<code class="user-select-all">{{ code }}</code>
							</div>
						</div>
					</div>
				</template>
				<template v-else>
					<div class="text-muted text-center py-3" v-if="this.mfaBusy && !this.mfaLink">
						<div class="spinner-border spinner-border-sm me-2"></div><LocaleText t="Loading..."></LocaleText>
					</div>
					<div class="row gy-3 align-items-center" v-if="this.mfaLink">
						<div class="col-md-5 text-center">
							<canvas id="mfa_qrcode" class="rounded-3 border"></canvas>
						</div>
						<div class="col-md-7 d-flex flex-column gap-2">
							<small class="text-muted">
								<LocaleText t="1. Scan this QR code with your authenticator application"></LocaleText>
							</small>
							<div class="p-2 bg-body-secondary rounded-3 border">
								<small class="text-muted d-block">
									<LocaleText t="Or enter this secret manually:"></LocaleText>
								</small>
								<code class="user-select-all">{{ this.mfaSecret }}</code>
							</div>
							<small class="text-muted">
								<LocaleText t="2. Enter the 6 digit code generated by your application"></LocaleText>
							</small>
							<div class="input-group">
								<input class="form-control form-control-sm rounded-start-3 text-center" maxlength="6"
								       inputmode="numeric" autocomplete="one-time-code" v-model="this.mfaCode">
								<button class="btn btn-primary btn-sm rounded-end-3 px-3" :disabled="this.mfaBusy"
								        @click="this.verifyMfa()">
									<i class="bi bi-check-lg me-1"></i><LocaleText t="Verify and enable"></LocaleText>
								</button>
							</div>
						</div>
					</div>
				</template>
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
									<button class="btn" :class="admin.TotpEnabled ? 'btn-outline-success' : 'btn-outline-secondary'"
									        title="MFA" @click="this.openMfa(admin)">
										<i class="bi" :class="admin.TotpEnabled ? 'bi-shield-lock-fill' : 'bi-shield-slash'"></i>
									</button>
									<button class="btn btn-outline-secondary" title="Edit" @click="this.startEdit(admin)">
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

