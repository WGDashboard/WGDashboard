<script setup async>
import {computed, onMounted, ref} from "vue";
import {axiosGet, requestURl} from "@/utilities/request.js";
import {clientStore} from "@/stores/clientStore.js";
import Configuration from "@/components/Configuration/configuration.vue";
import {onBeforeRouteLeave, useRouter} from "vue-router";
import axios from "axios";
const store = clientStore()
const loading = ref(true)

const configurations = computed(() => {
	return store.configurations
});
const refreshInterval = ref(undefined)
await store.getClientProfile();
onMounted(async () => {
	await store.getConfigurations()
	loading.value = false;

	refreshInterval.value = setInterval(async () => {
		await store.getConfigurations()
	}, 5000)
})

onBeforeRouteLeave(() => {
	clearInterval(refreshInterval.value)
});
const router = useRouter()
const signingOut = ref(false)
const signOut = async () => {
	clearInterval(refreshInterval.value)
	signingOut.value = true;
	await axios.get(requestURl('/api/signout')).then(() => {
		router.push('/signin')
	}).catch(() => {
		router.push('/signin')
	});
	store.newNotification("Sign out successful", "success")
}
</script>

<template>
<div class="p-sm-3">
	<div class="w-100 d-flex align-items-center">
		<a class="nav-link text-body border-start-0" aria-current="page" href="#">
			<strong>
				Hi, {{ store.clientProfile.Profile.Name ? store.clientProfile.Profile.Name : store.clientProfile.Email}}
			</strong>
		</a>
		<div class="ms-auto px-3 d-flex gap-2 nav-links">
			<RouterLink to="/settings" class=" text-body btn btn-outline-body rounded-3 ms-auto btn-sm" aria-current="page" href="#">
				<i class="bi bi-gear-fill me-sm-2"></i>
				<span>Settings</span>
			</RouterLink>
			<a role="button" @click="signOut()" class="btn btn-outline-danger rounded-3 btn-sm"
			   :class="{disabled: signingOut}"
			   aria-current="page">
				<i class="bi bi-box-arrow-left me-sm-2"></i>
				<span>
					{{ signingOut ? 'Signing out...':'Sign Out'}}
				</span>
			</a>
		</div>
	</div>

	<Transition name="app" mode="out-in">
		<div class="d-flex flex-column gap-3" v-if="!loading">
			<div class="p-3 d-flex flex-column gap-3" v-if="configurations.length > 0">
				<Configuration v-for="config in configurations" :config="config"></Configuration>
			</div>
			<div class="text-center text-muted" v-else>
				<small>No configuration available</small>
			</div>
		</div>
		<div v-else class="d-flex p-3">
			<div class="bg-body rounded-3 d-flex" style="width: 100%; height: 211px;">
				<div class="spinner-border m-auto"></div>
			</div>
		</div>
	</Transition>
</div>
</template>

<style scoped>
.nav-link{
	padding: 1rem 1rem;
}

@media screen and (max-width: 576px) {
	.nav-links a span{
		display: none;
	}
}
</style>