<template>
  <dl class="root">
    <div>
      <dt>Principal</dt>
      <dd>{{ formatter(principals) }}</dd>
    </div>
    <div>
      <dt>Interests</dt>
      <dd>{{ formatter(interests) }}</dd>
    </div>
    <div>
      <dt>Balance</dt>
      <dd>{{ formatter(balance) }}</dd>
    </div>
  </dl>
</template>

<script>
export default {
  props: ['principals', 'interests', 'balance', 'formatter'],
};
</script>

<style lang="scss" scoped>
.root {
  display: flex;
  > div {
    width: 33%;
  }
}
</style>
