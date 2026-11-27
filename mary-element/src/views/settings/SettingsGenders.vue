<template>
  <GenericSettingsView
    title="Gender Classifications"
    entityName="Gender"
    apiEndpoint="/genders"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
