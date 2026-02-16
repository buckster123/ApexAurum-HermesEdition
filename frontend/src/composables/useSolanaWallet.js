/**
 * Solana Wallet Composable — Phantom adapter for desktop payments.
 *
 * Detects Phantom extension, connects wallet, builds and signs
 * SOL + USDC transfer transactions with Solana Pay-compatible
 * reference keys for on-chain discovery.
 *
 * No @solana/spl-token dependency — USDC transfer instruction
 * built manually from raw instruction data.
 */

import { ref, computed } from 'vue'

// SPL Token constants (manual — no @solana/spl-token needed)
const TOKEN_PROGRAM_ID = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
const ASSOCIATED_TOKEN_PROGRAM_ID = 'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'

// Lazy-load @solana/web3.js (heavy — don't load until needed)
let _web3 = null
async function getWeb3() {
  if (!_web3) {
    _web3 = await import('@solana/web3.js')
  }
  return _web3
}

export function useSolanaWallet() {
  const connected = ref(false)
  const walletAddress = ref(null)
  const connecting = ref(false)
  const error = ref(null)

  const phantomAvailable = computed(() => !!window.phantom?.solana?.isPhantom)

  function getProvider() {
    if (window.phantom?.solana?.isPhantom) return window.phantom.solana
    return null
  }

  async function connect() {
    const provider = getProvider()
    if (!provider) {
      error.value = 'Phantom wallet not found'
      return false
    }

    connecting.value = true
    error.value = null

    try {
      const resp = await provider.connect()
      walletAddress.value = resp.publicKey.toString()
      connected.value = true
      return true
    } catch (err) {
      error.value = err.message || 'Wallet connection failed'
      return false
    } finally {
      connecting.value = false
    }
  }

  function disconnect() {
    const provider = getProvider()
    if (provider) {
      try { provider.disconnect() } catch (_) {}
    }
    connected.value = false
    walletAddress.value = null
  }

  /**
   * Build, sign, and send a SOL or USDC transfer via Phantom.
   *
   * @param {Object} opts
   * @param {string} opts.recipient - Recipient wallet address (base58)
   * @param {number} opts.amount - Amount in SOL or USDC (human units)
   * @param {string} opts.reference - Base58 reference pubkey for Solana Pay discovery
   * @param {string} opts.token - "SOL" or "USDC"
   * @param {string} opts.usdcMint - USDC mint address (base58)
   * @param {string} opts.rpcUrl - Solana RPC URL
   * @returns {{ signature: string } | null}
   */
  async function sendPayment({ recipient, amount, reference, token, usdcMint, rpcUrl }) {
    const provider = getProvider()
    if (!provider || !connected.value) {
      error.value = 'Wallet not connected'
      return null
    }

    error.value = null

    try {
      const web3 = await getWeb3()
      const { Connection, PublicKey, Transaction, SystemProgram, LAMPORTS_PER_SOL } = web3

      const connection = new Connection(rpcUrl, 'confirmed')
      const fromPubkey = new PublicKey(walletAddress.value)
      const toPubkey = new PublicKey(recipient)
      const referencePubkey = new PublicKey(reference)

      const transaction = new Transaction()

      if (token === 'SOL') {
        // Native SOL transfer
        const lamports = Math.round(amount * LAMPORTS_PER_SOL)
        transaction.add(
          SystemProgram.transfer({
            fromPubkey,
            toPubkey,
            lamports,
          })
        )
      } else {
        // USDC (SPL token) transfer — built manually
        const mintPubkey = new PublicKey(usdcMint)
        const tokenProgramId = new PublicKey(TOKEN_PROGRAM_ID)
        const ataProgramId = new PublicKey(ASSOCIATED_TOKEN_PROGRAM_ID)

        // Derive associated token accounts
        const [sourceAta] = PublicKey.findProgramAddressSync(
          [fromPubkey.toBuffer(), tokenProgramId.toBuffer(), mintPubkey.toBuffer()],
          ataProgramId
        )
        const [destAta] = PublicKey.findProgramAddressSync(
          [toPubkey.toBuffer(), tokenProgramId.toBuffer(), mintPubkey.toBuffer()],
          ataProgramId
        )

        // USDC has 6 decimals
        const rawAmount = BigInt(Math.round(amount * 1_000_000))

        // SPL Token transfer instruction (index 3)
        const data = Buffer.alloc(9)
        data.writeUInt8(3, 0)
        data.writeBigUInt64LE(rawAmount, 1)

        transaction.add({
          keys: [
            { pubkey: sourceAta, isSigner: false, isWritable: true },
            { pubkey: destAta, isSigner: false, isWritable: true },
            { pubkey: fromPubkey, isSigner: true, isWritable: false },
          ],
          programId: tokenProgramId,
          data,
        })
      }

      // Add reference pubkey for Solana Pay on-chain discovery
      // (non-signer, non-writable account on the transfer instruction)
      transaction.instructions[0].keys.push({
        pubkey: referencePubkey,
        isSigner: false,
        isWritable: false,
      })

      // Get recent blockhash and sign
      const { blockhash } = await connection.getLatestBlockhash('confirmed')
      transaction.recentBlockhash = blockhash
      transaction.feePayer = fromPubkey

      const { signature } = await provider.signAndSendTransaction(transaction)
      return { signature }
    } catch (err) {
      // User rejected or tx failed
      if (err.code === 4001 || err.message?.includes('rejected')) {
        error.value = 'Transaction cancelled'
      } else {
        error.value = err.message || 'Transaction failed'
      }
      return null
    }
  }

  return {
    connected,
    walletAddress,
    connecting,
    error,
    phantomAvailable,
    connect,
    disconnect,
    sendPayment,
  }
}
