<script>
import {fetchGet, fetchPost} from "../utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import Message from "@/components/messageCentreComponent/message.vue";
import RemoteServerList from "@/components/signInComponents/RemoteServerList.vue";
import {GetLocale} from "@/utilities/locale.js";
import LocaleText from "@/components/text/localeText.vue";
import SignInInput from "@/components/signIn/signInInput.vue";
import SignInTOTP from "@/components/signIn/signInTOTP.vue";
import SignInOIDC from "@/components/signIn/signInOIDC.vue";

export default {
	name: "signin",
	components: {SignInOIDC, SignInTOTP, SignInInput, LocaleText, RemoteServerList, Message},
	async setup(){
		const store = DashboardConfigurationStore()
		let theme = "dark"
		let totpEnabled = false;
		let version = undefined;
		if (!store.IsElectronApp){
			await Promise.all([
				fetchGet("/api/getDashboardTheme", {}, (res) => {
					theme = res.data
				}),
				fetchGet("/api/isTotpEnabled", {}, (res) => {
					totpEnabled = res.data
				}),
				fetchGet("/api/getDashboardVersion", {}, (res) => {
					version = res.data
				})
			]);
		}
		store.removeActiveCrossServer();
		return {store, theme, totpEnabled, version}
	},
	data(){
		return {
			data: {
				username: "",
				password: "",
				totp: "",
			},
			loginError: false,
			loginErrorMessage: "",
			loading: false,
			build: (typeof window !== "undefined" && window.__BUILD__) ? window.__BUILD__ : ""
		}
	},
	computed: {
		getMessages(){
			return this.store.Messages.filter(x => x.show)
		},
		applyLocale(key){
			return GetLocale(key)
		},
		formValid(){
			// The TOTP code is only required by the server when the account has MFA enabled,
			// so the field is always visible but never blocking here.
			return !!(this.data.username && this.data.password)
		},
		totpRequired(){
			// Offered as soon as a username is typed, and never required here. Asking the
			// server would disclose whether the account exists and whether it uses MFA
			// (see /api/admins/totp/required, answered uniformly for that reason).
			return String(this.data.username || "").trim().length > 0
		}
	},
	mounted() {
		this.checkMfaRedirect();
	},
	watch: {
		'data.username'(value){
			// The OTP field is offered for any non-empty username; drop a code that was
			// typed for a previous account. No server lookup: it would disclose the account.
			if (String(value || "").trim().length === 0){
				this.data.totp = "";
			}
		},
		'data.totp'(value){
			const formatted = this.formatOtp(value);
			if (formatted !== value){
				this.data.totp = formatted;
			}
		}
	},
	methods: {
		GetLocale,
		formatOtp(value){
			// The field accepts either a 6 digit TOTP or a recovery code (16 characters,
			// displayed as XXXX-XXXX-XXXX-XXXX). Recovery codes contain letters.
			const clean = String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
			if (/[A-Z]/.test(clean) || clean.length > 6){
				return clean.slice(0, 16).replace(/(.{4})/g, "$1-").replace(/-$/, "");
			}
			return clean.slice(0, 6);
		},
		checkMfaRedirect(){
			// If a session is already open on an account without MFA, go straight to the enrolment.
			// validateAuthentication is called first: it avoids a 401 (and a "session ended" toast)
			// when nobody is signed in yet.
			fetchGet("/api/validateAuthentication", {}, (auth) => {
				if (!auth.status) return;
				fetchGet("/api/admins/me", {}, (res) => {
					if (res.status && res.data && res.data.MfaSetupRequired === true){
						this.$router.push("/2FASetup");
					}
				});
			});
		},
		async auth(){
			if (this.formValid){
				this.loading = true
				await fetchPost("/api/authenticate", this.data, (response) => {
					if (response.status){
						this.loginError = false;
						this.$refs["signInBtn"].classList.add("signedIn")
						if (response.usedRecoveryCode){
							const remaining = response.recoveryCodesRemaining;
							this.store.newMessage("Server",
								"Signed in with a recovery code: it has been consumed and cannot be used again." +
								(typeof remaining === "number" ? " " + remaining + " code(s) left." : ""), "warning")
						}
						if (response.mfaSetupRequired){
							// MFA is mandatory: the account must enrol before using the dashboard
							this.$router.push('/2FASetup')
						}else if (response.message){
							this.$router.push('/welcome')
						}else{
							if (this.store.Redirect !== undefined){
								this.$router.push(this.store.Redirect)
							}else{
								this.$router.push('/')
							}
						}
					}else{
						this.store.newMessage("Server", response.message, "danger")
						document.querySelectorAll("input[required]").forEach(x => {
							x.classList.remove("is-valid")
							x.classList.add("is-invalid")
						});
						this.loading = false
					}
					
				})
			}else{
				document.querySelectorAll("input[required]").forEach(x => {
					if (x.value.length === 0){
						x.classList.remove("is-valid")
						x.classList.add("is-invalid")
					}else{
						x.classList.remove("is-invalid")
						x.classList.add("is-valid")
					}
				});
			}
		}
	}
}
</script>

<template>
	<div class="container-fluid login-container-fluid d-flex main flex-column py-4 text-body h-100" 
	     style="overflow-y: scroll"
	     :data-bs-theme="this.theme">
		<div class="login-box m-auto" >
			<div class="m-auto signInContainer" style="width: 700px;">
				<h4 class="mb-0 text-body">
					<LocaleText t="Welcome to"></LocaleText>
				</h4>
				<span class="dashboardLogo display-3">
					<strong>WGDashboard</strong>
				</span>
				<form @submit="(e) => {e.preventDefault(); this.auth();}"
				      class="mt-3"
				      v-if="!this.store.CrossServerConfiguration.Enable">
					<div class="form-floating mb-2">
						<input type="text"
						       required
						       :disabled="loading"
						       v-model="this.data.username"
						       name="username"
						       autocomplete="username"
						       autofocus
						       class="form-control rounded-3" id="username" placeholder="Username">
						<label for="floatingInput" class="d-flex">
							<i class="bi bi-person-circle me-2"></i>
							<LocaleText t="Username"></LocaleText>	
						</label>
					</div>
					<div class="form-floating mb-2">
						<input type="password"
						       required
						       :disabled="loading"
						       autocomplete="current-password"
						       v-model="this.data.password"
						       class="form-control rounded-3" id="password" placeholder="Password">
						<label for="floatingInput" class="d-flex">
							<i class="bi bi-key-fill me-2"></i>
							<LocaleText t="Password"></LocaleText>	
						</label>
					</div>
					<div class="form-floating mb-2" v-if="this.totpRequired">
						<input type="text"
						       id="totp"
						       :disabled="loading"
						       placeholder="totp"
						       v-model="this.data.totp"
						       class="form-control rounded-3"
						       maxlength="19"
						       inputmode="text"
						       autocomplete="one-time-code">
						<label for="floatingInput" class="d-flex">
							<i class="bi bi-lock-fill me-2"></i>
							<LocaleText t="OTP from your authenticator"></LocaleText>
						</label>
					</div>
					<small class="text-muted d-block mb-1" style="font-size: 0.75rem" v-if="this.totpRequired">
						<i class="bi bi-life-preserver me-1"></i>
						<LocaleText t="6 digits from your application, or one of your recovery codes"></LocaleText>
					</small>
					<button class="btn btn-lg btn-dark ms-auto mt-5 w-100 d-flex btn-brand signInBtn rounded-3" 
					        :disabled="this.loading || !this.formValid"
					        ref="signInBtn">
							<span v-if="!this.loading" class="d-flex w-100">
								<LocaleText t="Sign In"></LocaleText>
								<i class="ms-auto bi bi-chevron-right"></i>
							</span>
							<span v-else class="d-flex w-100 align-items-center">
								<LocaleText t="Signing In..."></LocaleText>
								<span class="spinner-border ms-auto spinner-border-sm" role="status"></span>
							</span>
					</button>
				</form>
				<RemoteServerList v-else></RemoteServerList>

				<div class="d-flex mt-3 flex-column" v-if="!this.store.IsElectronApp">
					<div class="form-check form-switch ms-auto">
						<input
							v-model="this.store.CrossServerConfiguration.Enable"
							:disabled="loading"
							class="form-check-input"
							type="checkbox"
							role="switch"
							id="flexSwitchCheckChecked">
						<label class="form-check-label" for="flexSwitchCheckChecked">
							<LocaleText t="Access Remote Server"></LocaleText>
						</label>
					</div>

					<SignInOIDC />
				</div>
			</div>
		</div>
		<div class="d-flex container-fluid align-items-center my-1 w-100">
			<small class="text-muted">
				WGDashboard <strong>{{ this.version }}</strong>
				<span v-if="this.build">· build <code>{{ this.build }}</code></span>
				| Made with ❤️ by
				<a href="https://github.com/WGDashboard"
				   class="text-decoration-none text-body"
				   target="_blank"><strong>WGDashboard</strong></a>
			</small>
			<a href="./client" target="_blank"
			   class="text-decoration-none ms-auto text-body"
			   style="white-space: nowrap">
				<small><i class="bi bi-box-arrow-up-right me-1"></i>
					<LocaleText t="Client App" /></small>
			</a>
		</div>
		<div class="messageCentre text-body position-absolute d-flex">
			<TransitionGroup name="message" tag="div"
			                 class="position-relative flex-sm-grow-0 flex-grow-1 d-flex align-items-end ms-sm-auto flex-column gap-2">
				<Message v-for="m in getMessages.slice().reverse()"
				         :message="m" :key="m.id"></Message>
			</TransitionGroup>
		</div>
	</div>
</template>

<style scoped>
@media screen and (max-width: 768px) {
	.login-box{
		width: 100% !important;
	}

	.login-box div{
		width: auto !important;
	}
}


</style>