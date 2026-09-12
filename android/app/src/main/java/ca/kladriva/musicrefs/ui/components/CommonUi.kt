package ca.kladriva.musicrefs.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ca.kladriva.musicrefs.ui.theme.BgDark
import ca.kladriva.musicrefs.ui.theme.Muted
import ca.kladriva.musicrefs.ui.theme.NeonCyan
import ca.kladriva.musicrefs.ui.theme.NeonPink
import ca.kladriva.musicrefs.ui.theme.OnDark

@Composable
fun GameTopBar(
    title: String,
    onHome: () -> Unit,
    trailing: (@Composable RowScope.() -> Unit)? = null,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        OutlinedButton(
            onClick = onHome,
            modifier = Modifier.heightIn(min = 48.dp),
            border = BorderStroke(1.dp, NeonCyan.copy(alpha = 0.5f)),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = NeonCyan),
        ) {
            Text("← Accueil", fontWeight = FontWeight.SemiBold)
        }
        Text(
            text = title,
            color = OnDark,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp,
            modifier = Modifier.weight(1f).padding(horizontal = 8.dp),
        )
        if (trailing != null) {
            Row(content = trailing)
        }
    }
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = NeonPink,
            contentColor = Color.White,
            disabledContainerColor = NeonPink.copy(alpha = 0.35f),
        ),
    ) {
        Text(text, fontWeight = FontWeight.Bold, fontSize = 16.sp)
    }
}

@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, NeonCyan.copy(alpha = 0.55f)),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = NeonCyan),
    ) {
        Text(text, fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
    }
}

@Composable
fun AppTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    singleLine: Boolean = true,
    imeAction: ImeAction = ImeAction.Next,
    onDone: (() -> Unit)? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 56.dp),
        singleLine = singleLine,
        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 16.sp, color = OnDark),
        keyboardOptions = KeyboardOptions(imeAction = imeAction),
        keyboardActions = KeyboardActions(onDone = { onDone?.invoke() }),
        shape = RoundedCornerShape(14.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = NeonPink,
            unfocusedBorderColor = Color.White.copy(alpha = 0.15f),
            focusedLabelColor = NeonPink,
            unfocusedLabelColor = Muted,
            cursorColor = NeonCyan,
            focusedTextColor = OnDark,
            unfocusedTextColor = OnDark,
            focusedContainerColor = BgDark.copy(alpha = 0.4f),
            unfocusedContainerColor = BgDark.copy(alpha = 0.4f),
        ),
    )
}

@Composable
fun ScoreHud(score: Int, streak: Int, highScore: Int, progress: String? = null) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        HudItem("Score", score.toString(), NeonPink)
        HudItem("Série", streak.toString(), NeonCyan)
        HudItem("Record", highScore.toString(), OnDark)
        if (progress != null) HudItem("Manche", progress, NeonCyan)
    }
}

@Composable
private fun HudItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, color = Muted, fontSize = 12.sp)
        Text(value, color = color, fontWeight = FontWeight.Black, fontSize = 18.sp)
    }
}

@Composable
fun ScreenScaffold(
    snackbarHostState: SnackbarHostState,
    topBar: @Composable () -> Unit = {},
    content: @Composable () -> Unit,
) {
    Column(
        Modifier
            .fillMaxWidth()
            .fillMaxSize(),
    ) {
        topBar()
        Column(
            Modifier
                .weight(1f, fill = true)
                .padding(horizontal = 16.dp),
        ) {
            content()
        }
        SnackbarHost(hostState = snackbarHostState)
        Spacer(Modifier.height(8.dp))
    }
}

@Composable
fun ModeToggle(
    selectedEasy: Boolean,
    onSelect: (Boolean) -> Unit,
) {
    Row(Modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        TextButton(
            onClick = { onSelect(false) },
            modifier = Modifier
                .weight(1f)
                .heightIn(min = 48.dp),
            colors = ButtonDefaults.textButtonColors(
                contentColor = if (!selectedEasy) NeonPink else Muted,
            ),
        ) {
            Text("Normal", fontWeight = if (!selectedEasy) FontWeight.Bold else FontWeight.Normal)
        }
        TextButton(
            onClick = { onSelect(true) },
            modifier = Modifier
                .weight(1f)
                .heightIn(min = 48.dp),
            colors = ButtonDefaults.textButtonColors(
                contentColor = if (selectedEasy) NeonCyan else Muted,
            ),
        ) {
            Text("Facile", fontWeight = if (selectedEasy) FontWeight.Bold else FontWeight.Normal)
        }
    }
}
