<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {initSystemThemeWatcher, resolveTheme} from "@/utilities/theme.js";
export default {
	name: "setup",
	components: {LocaleText},
	setup(){
		const store = DashboardConfigurationStore();
		return {store}
	},
	data(){
		return {
			setup: {
				username: "",
				newPassword: "",
				repeatNewPassword: "",
				enable_totp: true
			},
			loading: false,
			errorMessage: "",
			done: false
		}
	},
	computed: {
		resolvedTheme(){
			return resolveTheme(this.store.Configuration.Server.dashboard_theme)
		},
		goodToSubmit(){
			return this.setup.username 
				&& this.setup.newPassword.length >= 8
				&& this.setup.repeatNewPassword.length >= 8
				&& this.setup.newPassword === this.setup.repeatNewPassword
		}
	},
	mounted() {
		initSystemThemeWatcher();
	},
	methods: {
		submit(){
			this.loading = true
			fetchPost("/api/Welcome_Finish", this.setup, (res) => {
				if (res.status){
					this.done = true;
					this.$router.push('/2FASetup')
				}else{
					document.querySelectorAll("#createAccount input").forEach(x => x.classList.add("is-invalid"))
					this.errorMessage = res.message;
					document.querySelector(".login-container-fluid")
						.scrollTo({
							top: 0,
							left: 0,
							behavior: "smooth",
						})
				}
				this.loading = false
			})
		}
	}
}
</script>

<template>
	<div class="container-fluid login-container-fluid d-flex main pt-5 overflow-scroll" 
	     :data-bs-theme="resolvedTheme">
		<div class="m-auto text-body" style="width: 500px">
			<span class="dashboardLogo display-4">
				<LocaleText t="Nice to meet you!"></LocaleText>
			</span>
			<p class="mb-5">
				<LocaleText t="Please fill in the following fields to finish setup"></LocaleText>
				😊</p>
			<div>
				<h3>
					<LocaleText t="Create an account"></LocaleText>
				</h3>
				<div class="alert alert-danger" v-if="this.errorMessage">
					{{this.errorMessage}}
				</div>
				<div class="d-flex flex-column gap-3">
					<form id="createAccount" class="d-flex flex-column gap-2">
						<div class="form-group text-body">
							<label for="username" class="mb-1 text-muted">
								<small>
									<LocaleText t="Enter an username you like"></LocaleText>
								</small></label>
							<input type="text"
							       autocomplete="username"
							       v-model="this.setup.username"
							       class="form-control" id="username" name="username" required>
						</div>
						<div class="form-group text-body">
							<label for="password" class="mb-1 text-muted">
								<small>
									<LocaleText t="Enter a password"></LocaleText>
									<code>
										<LocaleText t="(At least 8 characters and make sure is strong enough!)"></LocaleText>
									</code>
								</small>
							</label>
							<input type="password"
							       autocomplete="new-password"
							       v-model="this.setup.newPassword"
							       class="form-control" id="password" name="password" required>
						</div>
						<div class="form-group text-body">
							<label for="confirmPassword" class="mb-1 text-muted">
								<small>
									<LocaleText t="Confirm password"></LocaleText>
								</small>
							</label>
							<input type="password"
							       autocomplete="confirm-new-password"
							       v-model="this.setup.repeatNewPassword"
							       class="form-control" id="confirmPassword" name="confirmPassword" required>
						</div>
					</form>
<!--					<div class="form-check form-switch">-->
<!--						<input class="form-check-input" type="checkbox" role="switch" id="enable_totp" -->
<!--						       v-model="this.setup.enable_totp">-->
<!--						<label class="form-check-label" -->
<!--						       for="enable_totp">Enable 2 Factor Authentication? <strong>Strongly recommended</strong></label>-->
<!--					</div>-->
<!--					<Suspense>-->
<!--						<Transition name="fade">-->
<!--							<Totp v-if="this.setup.enable_totp" @verified="this.setup.verified_totp = true"></Totp>-->
<!--						</Transition>-->
<!--					</Suspense>-->
					
					<button class="btn btn-dark btn-lg mb-5 d-flex btn-brand shadow align-items-center" 
					        ref="signInBtn"
					        :disabled="!this.goodToSubmit || this.loading || this.done" @click="this.submit()">
						<span class="d-flex align-items-center w-100" v-if="!this.loading && !this.done">
							<LocaleText t="Next"></LocaleText>
							
							<i class="bi bi-chevron-right ms-auto"></i></span>
						<span class="d-flex align-items-center w-100" v-else>
							<LocaleText t="Saving..."></LocaleText>
							<span class="spinner-border ms-auto spinner-border-sm" role="status">
							  <span class="visually-hidden">Loading...</span>
							</span></span>
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
