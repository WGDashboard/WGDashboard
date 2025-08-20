<script setup async>
import {clientStore} from "@/stores/clientStore.js";
import Profile from "@/components/Settings/profile.vue";
import UpdatePassword from "@/components/Settings/updatePassword.vue";
const store = clientStore()
await store.getClientProfile();
</script>

<template>
<div class="p-sm-3">
	<div class="w-100 d-flex align-items-center p-3">
		<RouterLink to="/" class=" text-body btn btn-outline-body rounded-3 btn-sm" aria-current="page" href="#">
			<i class="bi bi-chevron-left me-sm-2"></i>
			<span>Back</span>
		</RouterLink>
		<strong class="ms-auto">Settings</strong>
	</div>
	<Profile></Profile>
	<UpdatePassword v-if="store.clientProfile.SignInMethod === 'local'"></UpdatePassword>
</div>
</template>

<style scoped>

</style>