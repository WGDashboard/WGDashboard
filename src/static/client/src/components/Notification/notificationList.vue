<script setup>
import {clientStore} from "@/stores/clientStore.js";
import Notification from "@/components/Notification/notification.vue";
import {computed, onMounted} from "vue";
const store = clientStore()
const notifications = computed(() => {
	return store.notifications.filter(x => x.show).slice().reverse()
})
</script>

<template>
	<div class="messageCentre text-body position-absolute d-flex">
		<TransitionGroup name="message" tag="div"
		                 class="position-relative flex-sm-grow-0 flex-grow-1 d-flex align-items-end ms-sm-auto flex-column gap-2">
			<Notification v-for="n in notifications"
			         :notificationData="n" :key="n.id"></Notification>
		</TransitionGroup>
	</div>
</template>

<style scoped>
.message-move, /* apply transition to moving elements */
.message-enter-active,
.message-leave-active {
	transition: all 0.5s cubic-bezier(0.82, 0.58, 0.17, 1);
}

.message-enter-from,
.message-leave-to {
	filter: blur(2px);
	opacity: 0;
}

.message-enter-from{
	transform: translateY(-30px);
}

.message-leave-to{
	transform: translateY(30px);
}

.messageCentre{
	z-index: 9999;
	top: 1rem;
	right: 1rem;
}

@media screen and (max-width: 768px) {
	.messageCentre{
		width: calc(100% - 2rem);
	}
}
</style>