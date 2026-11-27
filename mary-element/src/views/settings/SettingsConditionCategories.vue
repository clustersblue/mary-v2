<template>
  <GenericSettingsView
    title="Medical Condition Categories"
    entityName="Condition Category"
    apiEndpoint="/condition-categories"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
