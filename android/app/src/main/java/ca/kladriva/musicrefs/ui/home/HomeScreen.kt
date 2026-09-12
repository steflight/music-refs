package ca.kladriva.musicrefs.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ca.kladriva.musicrefs.ui.components.PrimaryButton
import ca.kladriva.musicrefs.ui.components.SecondaryButton
import ca.kladriva.musicrefs.ui.theme.BgDark
import ca.kladriva.musicrefs.ui.theme.Muted
import ca.kladriva.musicrefs.ui.theme.NeonCyan
import ca.kladriva.musicrefs.ui.theme.NeonPink
import ca.kladriva.musicrefs.ui.theme.OnDark

@Composable
fun HomeScreen(
    onSolo: () -> Unit,
    onParty: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(BgDark, NeonPink.copy(alpha = 0.18f), BgDark, NeonCyan.copy(alpha = 0.12f)),
                ),
            ),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "MUSIC REFS",
                color = OnDark,
                fontWeight = FontWeight.Black,
                fontSize = 40.sp,
                letterSpacing = 6.sp,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = "Trouve l'artiste et le titre à partir d'une punchline.",
                color = Muted,
                textAlign = TextAlign.Center,
                fontSize = 16.sp,
                modifier = Modifier.fillMaxWidth(0.9f),
            )
            Spacer(Modifier.height(40.dp))
            PrimaryButton(text = "Jouer solo", onClick = onSolo)
            Spacer(Modifier.height(12.dp))
            SecondaryButton(text = "Partie amis", onClick = onParty)
        }
    }
}
