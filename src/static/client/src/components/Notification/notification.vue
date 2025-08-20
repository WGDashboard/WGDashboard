<script setup>
import {onMounted} from "vue";

const props = defineProps({
	notificationData: {
		id: "",
		show: true,
		content: "",
		time: "",
		status: ""
	}
})

let timeout = undefined;
const show = () => {
	props.notificationData.show = true;
	timeout = setTimeout(() => {
		dismiss()
	}, 5000)
}
const clearTime = () => clearTimeout(timeout)
const dismiss = () => props.notificationData.show = false;

onMounted(() => {
	show()
})

</script>

<template>
<div 
	@mouseenter="clearTime()"
	@mouseleave="notificationData.show ? show():undefined"
	:class="{
		'text-bg-success': notificationData.status === 'success',
		'text-bg-warning': notificationData.status === 'warning',
		'text-bg-danger': notificationData.status === 'danger'
	}"
	class="card shadow rounded-3 position-relative message ms-auto notification">
	<div class="card-body">
		<div class="d-flex align-items-center mb-2">
			<small>
				{{ notificationData.time.format("hh:mm A") }}
			</small>
			<small class="ms-auto">
				<a role="button" @click="dismiss()">
					Dismiss<i class="bi bi-x-lg ms-2"></i>
				</a>
			</small>
		</div>
		
		<span class="fw-medium">{{ notificationData.content }}</span>
	</div>
</div>
</template>

<style scoped>
.notification{
	width: 100%;
	word-break: break-word;
}

@media screen and (min-width: 576px) {
	.notification{
		width: 400px;
	}
}
</style>