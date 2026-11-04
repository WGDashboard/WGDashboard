<script setup lang="ts">
import {computed, ref} from "vue";
import {axiosPost, requestURl} from "@/utilities/request.js";
const email = ref("")
const loading = ref(false)
const verifyCode = ref(false)
import {clientStore} from "@/stores/clientStore.js";
import {useRouter} from "vue-router";
const store = clientStore()
const resendInterval = ref(undefined)
const resendCountdown = ref(120)
const requestToken = async (e) => {
	if (e) e.preventDefault()
	loading.value = true
	const result = await axiosPost("/api/resetPassword/generateResetToken", {
		Email: email.value
	})
	loading.value = false
	if (result.status){
		verifyCode.value = true
		resendCountdown.value = 120;
		resendInterval.value = setInterval(() => {
			resendCountdown.value --;
			if (resendCountdown.value === 0) clearInterval(resendInterval.value)
		}, 1000)
	}else{
		store.newNotification(result.message, "danger")
	}
}

const code = ref("")
const codeReady = computed(() => {
	return code.value.trim().length > 0
})
const codeValidated = ref(false)
const validateCode = async (e) => {
	if (e) e.preventDefault()
	loading.value = true
	let codeValidation = await axiosPost("/api/resetPassword/validateResetToken", {
		Email: email.value,
		Token: code.value.trim()
	})
	loading.value = false
	if (codeValidation.status){
		codeValidated.value = true
	}else{
		store.newNotification("Your reset token is either invalid or expired", "danger")
	}
}

const password = ref("")
const confirmPassword = ref("")
const passwordReady = computed(() => {
	return password.value && confirmPassword.value && password.value === confirmPassword.value
})
const router = useRouter()
const resetPassword = async (e) => {
	if (e) e.preventDefault()
	loading.value = true;
	let reset = await axiosPost("/api/resetPassword", {
		Email: email.value,
		Token: code.value.trim(),
		Password: password.value,
		ConfirmPassword: confirmPassword.value
	})
	if (reset.status){
		store.newNotification("Password reset! Now you can sign in with your new password", "success")

		await router.push('/signin')
	}else{
		store.newNotification(reset.message || "Password reset failed", "danger")
	}
}
</script>

<template>
<div class="p-3 p-sm-5">
	<Transition name="app" mode="out-in">
		<div v-if="!verifyCode">
			<RouterLink to="signin"
			            role="button"
			            class="btn btn-outline-body btn-sm rounded-3">
				<i class="me-2 bi bi-chevron-left"></i> Back
			</RouterLink>
			<div class="text-center">
				<h1 class="display-4">No worries</h1>
				<p class="text-muted">Enter the email address of your <strong>WGDashboard Client</strong> account below to receive a verification code</p>
			</div>
			<form class="mt-4 d-flex flex-column gap-3" @submit="e => requestToken(e)">
				<div class="form-floating">
					<input type="text"
					       required
					       :disabled="loading"
					       v-model="email"
					       name="email"
					       autocomplete="email"
					       autofocus
					       class="form-control rounded-3 border-0" id="email" placeholder="email">
					<label for="token" class="d-flex">
						<i class="bi bi-person-circle me-2"></i>
						Email
					</label>
				</div>
				<button
					:disabled="!email || loading"
					type="submit"
					class="btn btn-primary rounded-3 btn-body px-3 py-2 fw-bold">
				<span v-if="!loading" class="d-block">
					Continue <i class="bi bi-arrow-right ms-2"></i>
				</span>
					<span v-else class="d-block">
					Loading...<i class="ms-2 spinner-border spinner-border-sm"></i>
				</span>
				</button>
			</form>
		</div>
		<div v-else-if="verifyCode && !codeValidated">
			<a role="button" class="text-decoration-none text-body" @click="verifyCode = false; code = ''">
				<i class="me-2 bi bi-chevron-left"></i> Back
			</a>
			<div class="text-center">
				<h1 class="display-4">Almost there</h1>
				<p class="text-muted">Enter the reset token you received below to reset your password</p>
				<p class="text-muted" v-if="resendCountdown > 0">Didn't get the code? Maybe check your Spam/Junk mailbox. You can get another code in {{ resendCountdown }} seconds.</p>
				<a role="button"
				   :class="{disabled: loading}"
				   @click="requestToken()" v-else-if="resendCountdown === 0 && !loading">Resend</a>
			</div>
			<form class="mt-4 d-flex flex-column gap-3" @submit="e => validateCode(e)">
				<div class="form-floating">
					<input type="text"
					       required
					       :disabled="loading"
					       v-model="code"
					       autocomplete="off"
					       autocapitalize="off"
					       spellcheck="false"
					       autofocus
					       class="form-control rounded-3 border-0" id="token" placeholder="token">
					<label for="token" class="d-flex">
						<i class="bi bi-person-circle me-2"></i>
						Password Reset Token
					</label>
				</div>
				<button
					:disabled="!codeReady || loading"
					type="submit"
					class="btn btn-primary rounded-3 btn-body px-3 py-2 fw-bold">
				<span v-if="!loading" class="d-block">
					Continue <i class="bi bi-arrow-right ms-2"></i>
				</span>
					<span v-else class="d-block">
					Loading...<i class="ms-2 spinner-border spinner-border-sm"></i>
				</span>
				</button>
			</form>
		</div>
		<div v-else-if="verifyCode && codeValidated">
			<a role="button" class="text-decoration-none text-body" @click="verifyCode = false; code = ''; codeValidated = false">
				<i class="me-2 bi bi-chevron-left"></i> Back
			</a>
			<div class="text-center">
				<h1 class="display-4">Last step</h1>
				<p class="text-muted">Enter your new password below</p>
			</div>
			<form class="mt-4 d-flex flex-column gap-3" @submit="(e) => resetPassword(e)">
				<div class="form-floating">
					<input type="password"
					       required
					       :disabled="loading"
					       v-model="password"
					       name="password"
					       autocomplete="new-password"
					       autofocus
					       class="form-control rounded-3" id="password" placeholder="password">
					<label for="password" class="d-flex">
						<i class="bi bi-key me-2"></i>
						Password
					</label>
				</div>
				<div class="form-floating">
					<input type="password"
					       required
					       :disabled="loading"
					       v-model="confirmPassword"
					       name="confirm_password"
					       autocomplete="new-password"
					       autofocus
					       class="form-control rounded-3" id="confirm_password" placeholder="confirm_password">
					<label for="confirm_password" class="d-flex">
						<i class="bi bi-key me-2"></i>
						Confirm Password
					</label>
					<div id="validationServer03Feedback" class="invalid-feedback">
						Passwords does not match
					</div>
				</div>
				<button
					:disabled="!passwordReady || loading"
					type="submit"
					class="btn btn-primary rounded-3 btn-body px-3 py-2 fw-bold">
					<span v-if="!loading" class="d-block">
						Continue <i class="bi bi-arrow-right ms-2"></i>
					</span>
					<span v-else class="d-block">
						Loading...<i class="ms-2 spinner-border spinner-border-sm"></i>
					</span>
				</button>
			</form>
		</div>
	</Transition>
	<div>
		<hr class="my-4">
		<div class="d-flex align-items-center">
					<span class="text-muted">
						Don't have an account yet?
					</span>
			<RouterLink  to="/signup"
			             class="text-body text-decoration-none ms-auto fw-bold btn btn-sm btn-outline-body rounded-3">
				Sign Up
			</RouterLink>
		</div>
	</div>
</div>
</template>

<style scoped>

</style>