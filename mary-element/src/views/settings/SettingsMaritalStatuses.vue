<template>
  <GenericSettingsView
    title="Marital Statuses"
    entityName="Marital Status"
    apiEndpoint="/marital-statuses"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
