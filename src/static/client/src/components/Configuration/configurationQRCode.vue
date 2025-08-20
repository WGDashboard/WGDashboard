<script setup>
import Qrcode from "@/components/SignIn/qrcode.vue";

const props = defineProps([
	'qrcodeData'
])

const emits = defineEmits([
	'back'
])

</script>

<template>
<div class="p-2 position-fixed top-0 start-0 vw-100 vh-100 d-flex qrcodeContainer p-3 overflow-scroll">
	<div class="m-auto d-flex gap-3 flex-column p-3">
		<div>
			<a role="button" @click="emits('back')" class="btn btn-body rounded-3 btn-sm">
				<i class="me-2 bi bi-x-lg"></i> Dismiss
			</a>
		</div>
		<Qrcode :content="props.qrcodeData"></Qrcode>
		<button class="btn bg-primary-subtle border-primary-subtle rounded-3">
			<i class="bi bi-download me-2"></i>Download
		</button>
	</div>
</div>
</template>

<style scoped>

.qrcodeContainer{
	background-color: #00000050;
	backdrop-filter: blur(8px) brightness(0.8);
	z-index: 9999;
}
</style>