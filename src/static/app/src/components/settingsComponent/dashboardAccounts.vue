<script setup>
import {onMounted, reactive, ref} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

const store = DashboardConfigurationStore()
const accounts = ref([])
const current = ref(undefined)
const showNew = ref(false)
const loading = ref(false)
const confirmDelete = ref(undefined)
const newAccount = reactive({
	username: "",
	password: "",
	repeatPassword: ""
})

const load = async () => {
	await fetchGet("/api/accounts", {}, (res) => {
		if (res.status){
			accounts.value = res.data.accounts
			current.value = res.data.current
		}
	})
}

const resetNew = () => {
	newAccount.username = ""
	newAccount.password = ""
	newAccount.repeatPassword = ""
	showNew.value = false
}

const addAccount = async () => {
	loading.value = true
	await fetchPost("/api/accounts/add", newAccount, (res) => {
		if (res.status){
			accounts.value = res.data
			store.newMessage("Server", "Account created", "success")
			resetNew()
		}else{
			store.newMessage("Server", res.message, "danger")
		}
		loading.value = false
	})
}

const deleteAccount = async (username) => {
	loading.value = true
	await fetchPost("/api/accounts/delete", {username: username}, (res) => {
		if (res.status){
			accounts.value = res.data
			store.newMessage("Server", "Account deleted", "success")
		}else{
			store.newMessage("Server", res.message, "danger")
		}
		confirmDelete.value = undefined
		loading.value = false
	})
}

onMounted(() => load())
</script>

<template>
	<div class="card rounded-3">
		<div class="card-header d-flex align-items-center">
			<h6 class="my-2">
				<i class="bi bi-person-badge-fill me-2"></i>
				<LocaleText t="Dashboard Accounts"></LocaleText>
			</h6>
			<button class="btn btn-sm bg-primary-subtle text-primary-emphasis border-1 border-primary-subtle rounded-3 shadow-sm ms-auto"
			        v-if="!showNew"
			        @click="showNew = true">
				<i class="bi bi-plus-circle-fill me-2"></i>
				<LocaleText t="Account"></LocaleText>
			</button>
		</div>
		<div class="card-body d-flex flex-column gap-2">
			<form class="card rounded-3" v-if="showNew" @submit.prevent="addAccount()">
				<div class="card-body d-flex flex-column gap-2">
					<div class="row g-2">
						<div class="col-sm">
							<label for="newAccountUsername" class="text-muted mb-1">
								<strong><small><LocaleText t="Username"></LocaleText></small></strong>
							</label>
							<input class="form-control" id="newAccountUsername" autocomplete="off"
							       :disabled="loading" v-model="newAccount.username">
						</div>
						<div class="col-sm">
							<label for="newAccountPassword" class="text-muted mb-1">
								<strong><small><LocaleText t="Password"></LocaleText></small></strong>
							</label>
							<input class="form-control" type="password" id="newAccountPassword" autocomplete="new-password"
							       :disabled="loading" v-model="newAccount.password">
						</div>
						<div class="col-sm">
							<label for="newAccountRepeatPassword" class="text-muted mb-1">
								<strong><small><LocaleText t="Repeat Password"></LocaleText></small></strong>
							</label>
							<input class="form-control" type="password" id="newAccountRepeatPassword" autocomplete="new-password"
							       :disabled="loading" v-model="newAccount.repeatPassword">
						</div>
					</div>
					<div class="d-flex gap-2 ms-auto">
						<button type="button" class="btn bg-secondary-subtle text-secondary-emphasis border-1 border-secondary-subtle rounded-3 shadow-sm"
						        :disabled="loading" @click="resetNew()">
							<LocaleText t="Cancel"></LocaleText>
						</button>
						<button type="submit" class="btn bg-success-subtle text-success-emphasis border-1 border-success-subtle rounded-3 shadow-sm"
						        :disabled="loading || !newAccount.username || newAccount.password.length < 8 || newAccount.password !== newAccount.repeatPassword">
							<i class="bi bi-save2-fill me-2"></i>
							<LocaleText t="Save"></LocaleText>
						</button>
					</div>
				</div>
			</form>
			<div class="list-group">
				<div class="list-group-item d-flex align-items-center gap-2" v-for="a in accounts" :key="a.username">
					<i class="bi bi-person-fill"></i>
					<span>{{ a.username }}</span>
					<span class="badge rounded-pill text-bg-primary" v-if="a.primary">
						<LocaleText t="Primary"></LocaleText>
					</span>
					<span class="badge rounded-pill text-bg-secondary" v-if="a.username === current">
						<LocaleText t="You"></LocaleText>
					</span>
					<span class="badge rounded-pill text-bg-success" v-if="a.enable_totp && a.totp_verified">MFA</span>
					<div class="ms-auto d-flex gap-2" v-if="!a.primary && a.username !== current">
						<template v-if="confirmDelete === a.username">
							<button class="btn btn-sm bg-danger-subtle text-danger-emphasis border-1 border-danger-subtle rounded-3"
							        :disabled="loading" @click="deleteAccount(a.username)">
								<LocaleText t="Yes"></LocaleText>
							</button>
							<button class="btn btn-sm bg-secondary-subtle text-secondary-emphasis border-1 border-secondary-subtle rounded-3"
							        :disabled="loading" @click="confirmDelete = undefined">
								<LocaleText t="No"></LocaleText>
							</button>
						</template>
						<button class="btn btn-sm bg-danger-subtle text-danger-emphasis border-1 border-danger-subtle rounded-3"
						        v-else :disabled="loading" @click="confirmDelete = a.username">
							<i class="bi bi-trash-fill"></i>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
