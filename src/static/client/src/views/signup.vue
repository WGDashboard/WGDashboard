<script setup>
import {computed, onMounted, reactive, ref} from "vue";
import axios from "axios";
import {clientStore} from "@/stores/clientStore.js";
import {requestURl} from "@/utilities/request.js";
import {useRouter} from "vue-router";
const store = clientStore()

const formData = reactive({
	Email: "",
	Password: "",
	ConfirmPassword: ""
})
const loading = ref(false)
const router = useRouter()

const signUp = async (e) => {
	e.preventDefault()
	if (!formFilled){
		store.newNotification("Please fill in all fields", "warning")
		return;
	}
	if (validatePassword){
		loading.value = true
		await axios.post(requestURl('/api/signup'), formData).then((res) => {
			let data = res.data
			if (!data.status){
				store.newNotification(data.message, "danger")
				loading.value = false
			}else{
				store.newNotification("Sign up successfully!", "success")
				router.push({
					path: '/signin',
					query: {
						Email: formData.Email
					}
				})
			}
		})
	}

}

const validatePassword = computed(() => {
	if (formData.Password && formData.ConfirmPassword){
		return formData.Password === formData.ConfirmPassword;
	}
	return false
})

const formFilled = computed(() => {
	return Object.values(formData).find(x => !x) === undefined
})

onMounted(() => {
	document.querySelectorAll("input[type=password]").forEach(e => e.addEventListener('blur', () => {
		if (formData.Password && formData.ConfirmPassword){
			document.querySelectorAll("input[type=password]").forEach(x => {
				if (!validatePassword.value){
					x.classList.add("is-invalid")
				}else {
					x.classList.remove("is-invalid")
				}
			})
		}
	}))
})
</script>

<template>
	<div class="p-3 p-sm-5">
		<div class="text-center">
			<h1 class="display-4">Hi, nice to meet you</h1>
			<p class="text-muted">Sign up to use <strong>WGDashboard Client</strong></p>
		</div>
		<form class="mt-4 d-flex flex-column gap-3" @submit="e => signUp(e)">
			<div class="form-floating">
				<input type="text"
				       :disabled="loading"
				       required
				       v-model="formData.Email"
				       name="email"
				       autocomplete="email"
				       autofocus
				       class="form-control rounded-3" id="email" placeholder="email">
				<label for="email" class="d-flex">
					<i class="bi bi-person-circle me-2"></i>
					Email
				</label>
			</div>
			<div class="row gx-3">
				<div class="col-6">
					<div class="form-floating">
						<input type="password"
						       required
						       :disabled="loading"
						       v-model="formData.Password"
						       name="password"
						       autocomplete="new-password"
						       autofocus
						       class="form-control rounded-3" id="password" placeholder="password">
						<label for="password" class="d-flex">
							<i class="bi bi-key me-2"></i>
							Password
						</label>
					</div>
				</div>
				<div class="col-6">
					<div class="form-floating">
						<input type="password"
						       required
						       :disabled="loading"
						       v-model="formData.ConfirmPassword"
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
				</div>
			</div>


			<button
				:disabled="!formFilled || !validatePassword || loading"
				class=" btn btn-primary rounded-3 btn-body px-3 py-2 fw-bold">
				<span v-if="!loading" class="d-block">
						Continue <i class="ms-2 bi bi-arrow-right"></i>
					</span>
				<span v-else class="d-block">
						Loading...
						<i class="spinner-border spinner-border-sm"></i>
					</span>
			</button>
		</form>
		<div>
			<hr class="my-4">
			<div class="d-flex align-items-center">
					<span class="text-muted">
						Already have an account?
					</span>
				<RouterLink  to="/signin" class="text-body text-decoration-none ms-auto fw-bold btn btn-sm btn-outline-body rounded-3">
					Sign In
				</RouterLink>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>