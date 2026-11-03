import {createTheme} from '@mui/material/styles';

export const theme=createTheme({
  palette:{
    mode:'light',
    primary:{main:'#0a3b72',dark:'#071d3d',light:'#2d6fac'},
    secondary:{main:'#d79a22'},
    background:{default:'#f4f7fb',paper:'#ffffff'},
    success:{main:'#16805b'},warning:{main:'#c78013'},error:{main:'#c33b3b'},
  },
  shape:{borderRadius:12},
  typography:{
    fontFamily:'Inter, Segoe UI, Arial, sans-serif',
    h4:{fontWeight:800,letterSpacing:'-.035em'},
    h5:{fontWeight:800,letterSpacing:'-.025em'},
    h6:{fontWeight:750},
    button:{fontWeight:750,textTransform:'none'},
  },
  components:{
    MuiCard:{styleOverrides:{root:{border:'1px solid #e0e8f2',boxShadow:'0 8px 28px rgba(7,29,61,.06)'}}},
    MuiButton:{styleOverrides:{root:{boxShadow:'none'}}},
    MuiTextField:{defaultProps:{size:'small'}},
    MuiDialog:{styleOverrides:{paper:{backgroundImage:'none'}}},
  },
});

