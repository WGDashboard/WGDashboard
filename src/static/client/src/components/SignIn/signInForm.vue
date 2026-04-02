<script setup>
import {computed, reactive, ref} from "vue";
import {clientStore} from "@/stores/clientStore.js";
import axios from "axios";
import {axiosPost, requestURl} from "@/utilities/request.js";
import {useRoute, useRouter} from "vue-router";
import Oidc from "@/components/SignIn/oidc/oidc.vue";
const loading = ref(false)
const formData = reactive({
	Email: "",
	Password: ""
});
const emits = defineEmits(['totpToken'])

const totpToken = ref("")
const store = clientStore()
const signIn = async (e) => {
	e.preventDefault();
	if (!formFilled){
		store.newNotification("Please fill in all fields", "warning")
		return;
	}
	loading.value = true;

	const data = await axiosPost("/api/signin", formData)
	if (!data.status){
		store.newNotification(data.message, "danger")
		loading.value = false;
	}else{
		emits("totpToken", data.message)
	}
}

const formFilled = computed(() => {
	return Object.values(formData).find(x => !x) === undefined
})

// const router = useRouter()
const route = useRoute()
if (route.query.Email){
	formData.Email = route.query.Email
}

</script>

<template>
	<div>
		<div class="text-center">
			<h1 class="display-4">Welcome</h1>
			<p class="text-muted">Sign in to access your <strong>WGDashboard Client</strong> account</p>
		</div>
		<Oidc></Oidc>
		<form class="mt-4 d-flex flex-column gap-3" @submit="e => signIn(e)">
			<div class="form-floating">
				<input type="text"
				       required
				       :disabled="loading"
				       v-model="formData.Email"
				       name="email"
				       autocomplete="email"
				       autofocus
				       class="form-control rounded-3 border-0" id="email" placeholder="email">
				<label for="email" class="d-flex">
					<i class="bi bi-person-circle me-2"></i>
					Email
				</label>
			</div>
			<div class="form-floating">
				<input type="password"
				       required
				       :disabled="loading"
				       v-model="formData.Password"
				       name="password"
				       autocomplete="current-password"
				       class="form-control rounded-3  border-0" id="password" placeholder="Password">
				<label for="password" class="d-flex">
					<i class="bi bi-key me-2"></i>
					Password
				</label>
			</div>
			<div class="d-flex">
				<RouterLink to="forgotPassword"

				   class="text-body text-decoration-none ms-auto btn btn-sm rounded-3">
					Forgot Password?
				</RouterLink>
			</div>
			<button
				:disabled="!formFilled || loading"
				class="btn btn-primary rounded-3 btn-body px-3 py-2 fw-bold">
				<span v-if="!loading" class="d-block">
					Sign In
				</span>
				<span v-else class="d-block">
					Loading...<i class="ms-2 spinner-border spinner-border-sm"></i>
				</span>
			</button>
		</form>
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