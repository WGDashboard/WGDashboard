<script setup async>

import {axiosGet} from "@/utilities/request.js";
import {ref} from "vue";
import OidcBtn from "@/components/SignIn/oidc/oidcBtn.vue";

const providerExist = ref(false)
const providers = ref(undefined)
const getProviders = await axiosGet("/api/signin/oidc/providers")
if (getProviders){
	providerExist.value = true;
	providers.value = getProviders.data
	console.log(providers.value)
}

</script>

<template>
	<div v-if="providers">
		<hr>
		<h6 class="text-center text-muted mb-3">
			<small>Sign in with</small>
		</h6>
		<div class="d-flex gap-2">
			<suspense>
				<OidcBtn :provider="provider" :name="name" v-for="(provider, name) in providers"></OidcBtn>
				<template #fallback>
					<a class="btn btn-sm btn-outline-body rounded-3 w-100 disabled">
						Loading...
					</a>
				</template>
			</suspense>
		</div>
		<hr>
	</div>
</template>

<style scoped>

</style>