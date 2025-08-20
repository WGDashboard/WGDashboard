<script setup>
import SignInForm from "@/components/SignIn/signInForm.vue";
import {ref} from "vue";
import TotpForm from "@/components/SignIn/totpForm.vue";

const checkTotp = ref("")

</script>

<template>
	<div class="p-3 p-sm-5">
		<Transition name="app" mode="out-in">
			<SignInForm
				@totpToken="token => { checkTotp = token }"
				v-if="!checkTotp"></SignInForm>
			<TotpForm
				@clearToken="checkTotp = ''"
				:totp-token="checkTotp"
				v-else></TotpForm>
		</Transition>
	</div>
</template>

<style scoped>

</style>