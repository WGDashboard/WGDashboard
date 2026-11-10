<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import QRCode from "qrcode";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "totp",
	components: {LocaleText},
	setup(){
		const store = DashboardConfigurationStore();
		return {store};
	},
	data(){
		return {
			mode: null,          // "admin" (mandatory enrolment) or "welcome" (legacy wizard)
			adminID: null,
			username: "",
			postponeAllowed: false,
			setupRequired: false,
			link: "",
			totp: "",
			verified: false,
			codes: [],
			busy: true,
			message: ""
		}
	},
	mounted() {
		this.init();
	},
	methods: {
		init(){
			fetchGet("/api/admins/me", {}, (me) => {
				if (me.status && me.data && me.data.AdminID){
					this.mode = "admin";
					this.adminID = me.data.AdminID;
					this.username = me.data.Username || "";
					this.postponeAllowed = me.data.MfaPostponeAllowed === true;
					// MFA is only compulsory when the server asks for it: with the default
					// require_mfa=false the page must stay skippable.
					this.setupRequired = me.data.MfaSetupRequired === true;
					fetchPost("/api/admins/totp/start", {AdminID: this.adminID}, (res) => {
						this.busy = false;
						if (res.status && res.data){
							this.link = res.data.Link;
							this.renderQr();
						}else{
							this.message = res.message || "";
						}
					});
				}else{
					this.mode = "welcome";
					this.busy = false;
					fetchGet("/api/Welcome_GetTotpLink", {}, (res) => {
						if (res.status){
							this.link = res.data;
							this.renderQr();
						}
					});
				}
			});
		},
		renderQr(){
			this.$nextTick(() => {
				const canvas = document.getElementById("qrcode");
				if (canvas && this.link){
					QRCode.toCanvas(canvas, this.link, {width: 220, margin: 1}, () => {});
				}
			});
		},
		validate(){
			const input = document.querySelector("#totp");
			input.classList.remove("is-invalid", "is-valid");
			if (!/^[0-9]{6}$/.test(this.totp)){
				input.classList.add("is-invalid");
				return;
			}
			if (this.mode === "admin"){
				fetchPost("/api/admins/totp/verify", {AdminID: this.adminID, code: this.totp}, (res) => {
					if (res.status){
						this.verified = true;
						input.classList.add("is-valid");
						this.generateCodes();
					}else{
						input.classList.add("is-invalid");
						this.message = res.message || "";
					}
				});
			}else{
				fetchPost("/api/Welcome_VerifyTotpLink", {totp: this.totp}, (res) => {
					if (res.status){
						this.verified = true;
						input.classList.add("is-valid");
					}else{
						input.classList.add("is-invalid");
					}
				});
			}
		},
		generateCodes(){
			fetchPost("/api/admins/totp/recoveryCodes", {AdminID: this.adminID}, (res) => {
				if (res.status && res.data){
					this.codes = res.data.Codes || [];
				}
			});
		},
		finish(){
			this.$router.push("/");
		},
		signOut(){
			fetchGet("/api/signout", {}, () => {
				this.store.Redirect = undefined;
				this.$router.push("/signin");
			});
		},
		postpone(){
			fetchPost("/api/admins/totp/postpone", {}, (res) => {
				if (res.status){
					this.store.newMessage("WGDashboard",
						"MFA setup postponed for this session only: you will be asked again at your next sign in.",
						"warning");
					this.$router.push("/");
				}else{
					this.store.newMessage("Server", res.message, "danger");
				}
			});
		},
		copyCodes(){
			const text = this.codes.join("\n");
			if (navigator.clipboard){
				navigator.clipboard.writeText(text);
				this.store.newMessage("Server", "Recovery codes copied", "success");
			}
		},
		downloadCodes(){
			if (this.codes.length === 0) return;
			const username = this.username || "administrateur";
			const safeName = username.replace(/[^A-Za-z0-9._@-]/g, "_");
			const now = new Date();
			const content = [
				"WGDashboard - codes de secours MFA",
				"Compte      : " + username,
				"Generes le  : " + now.toLocaleString(),
				"",
				"Chaque code ne peut etre utilise qu'une seule fois.",
				"Conservez ce fichier en lieu sur, hors du serveur.",
				"",
				...this.codes.map((c, i) => (i + 1) + ". " + c),
				""
			].join("\n");
			const blob = new Blob([content], {type: "text/plain;charset=utf-8"});
			const url = URL.createObjectURL(blob);
			const link = document.createElement("a");
			link.href = url;
			link.download = "codes-secours-" + safeName + "-" + now.toISOString().slice(0, 10) + ".txt";
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);
			this.store.newMessage("Server", "Recovery codes downloaded", "success");
		}
	},
	watch: {
		totp(newValue){
			if (newValue.length === 6){
				this.validate();
			}
		}
	}
}
</script>

<template>
	<div class="container-fluid login-container-fluid d-flex main pt-5 overflow-scroll"
	     :data-bs-theme="(this.store.Configuration && this.store.Configuration.Server && this.store.Configuration.Server.dashboard_theme) || 'dark'">
		<div class="m-auto text-body" style="width: 500px">
			<div class="d-flex flex-column">
				<div class="mb-2 d-flex align-items-center gap-2">
					<h1 class="dashboardLogo display-4 mb-0">
						<LocaleText t="Multi-Factor Authentication (MFA)"></LocaleText>
					</h1>
					<span class="badge text-bg-warning" v-if="this.mode === 'admin'">
						<LocaleText t="Required"></LocaleText>
					</span>
				</div>
				<div class="text-muted mb-3" v-if="this.busy">
					<div class="spinner-border spinner-border-sm me-2"></div><LocaleText t="Loading..."></LocaleText>
				</div>
				<div class="alert alert-danger py-2" v-if="this.message">{{ this.message }}</div>

				<template v-if="!this.verified">
					<p class="mb-2"><small class="text-muted">
						<LocaleText t="1. Please scan the following QR Code to generate TOTP with your choice of authenticator"></LocaleText>
					</small></p>
					<canvas id="qrcode" class="rounded-3 mb-2"></canvas>
					<div class="p-3 bg-body-secondary rounded-3 border mb-3" v-if="this.link">
						<p class="text-muted mb-0">
							<small>
								<LocaleText t="Or you can click the link below:"></LocaleText>
							</small>
						</p><a :href="this.link"><code style="line-break: anywhere">{{ this.link }}</code></a>
					</div>
					<label for="totp" class="mb-2">
						<small class="text-muted">
							<LocaleText t="2. Enter the TOTP generated by your authenticator to verify"></LocaleText>
						</small>
					</label>
					<div class="form-group mb-2">
						<input class="form-control text-center totp"
						       id="totp" maxlength="6" type="text" inputmode="numeric" autocomplete="one-time-code"
						       v-model="this.totp">
						<div class="invalid-feedback">
							<LocaleText t="TOTP does not match."></LocaleText>
						</div>
						<div class="valid-feedback">
							<LocaleText t="TOTP verified!"></LocaleText>
						</div>
					</div>
				</template>

				<template v-else>
					<div class="alert alert-success py-2">
						<i class="bi bi-shield-check me-1"></i>
						<LocaleText t="MFA is now enabled for your account"></LocaleText>
					</div>
					<div v-if="this.codes.length > 0">
						<p class="mb-2">
							<small class="text-muted">
								<LocaleText t="Save these recovery codes now: each one can be used once to sign in if you lose your authenticator. They will not be shown again."></LocaleText>
							</small>
						</p>
						<div class="p-3 bg-body-secondary rounded-3 border mb-2">
							<div class="row row-cols-2 g-2">
								<div class="col" v-for="code in this.codes" :key="code">
									<code class="user-select-all">{{ code }}</code>
								</div>
							</div>
						</div>
						<div class="d-flex gap-2">
							<button class="btn btn-sm bg-secondary-subtle text-secondary-emphasis rounded-3 px-3" @click="this.copyCodes()">
								<i class="bi bi-clipboard-fill me-1"></i><LocaleText t="Copy"></LocaleText>
							</button>
							<button class="btn btn-sm btn-primary rounded-3 px-3" @click="this.downloadCodes()">
								<i class="bi bi-download me-1"></i><LocaleText t="Download"></LocaleText>
							</button>
						</div>
					</div>
				</template>
			</div>
			<hr>
			<div class="d-flex gap-3 mt-5 flex-column">
				<RouterLink
					to="/"
					v-if="!this.verified && (!this.setupRequired || this.postponeAllowed)"
					class="btn bg-secondary-subtle text-secondary-emphasis rounded-3 flex-grow-1 btn-lg border-1 border-secondary-subtle shadow d-flex">
					<LocaleText t="I don't need MFA"></LocaleText>
					<i class="bi bi-chevron-right ms-auto"></i>
				</RouterLink>
				<RouterLink
					to="/"
					v-if="this.verified"
					class="btn btn-dark btn-lg d-flex btn-brand shadow align-items-center flex-grow-1 rounded-3">
					<LocaleText t="Complete"></LocaleText>
					<i class="bi bi-chevron-right ms-auto"></i>
				</RouterLink>
				<div class="d-flex gap-2 align-items-center justify-content-center flex-wrap">
					<button class="btn btn-outline-secondary btn-sm rounded-3 d-flex align-items-center px-3"
					        v-if="!this.verified && this.mode === 'admin' && this.postponeAllowed"
					        @click="this.postpone()">
						<i class="bi bi-skip-forward-fill me-2"></i>
						<LocaleText t="Continue without MFA"></LocaleText>
					</button>
					<button class="btn btn-link text-muted text-decoration-none" @click="this.signOut()">
						<i class="bi bi-box-arrow-right me-1"></i>
						<LocaleText t="Sign out"></LocaleText>
						<small v-if="this.username">({{ this.username }})</small>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
</style>
